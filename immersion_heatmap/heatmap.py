import numpy as np
import pandas as pd
import seaborn as sns
import click
import os
import matplotlib.colors as mcolors
from matplotlib import colormaps
import logging
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)


def modify_cmap(cmap_name, zero_color="black", nan_color="black", truncate_high=0.7):
    """
    Modify a colormap to have specific colors for 0 and NaN values, and truncate the upper range.

    Parameters:
    - cmap_name: str, the name of the base colormap.
    - zero_color: str or tuple, color to be used for 0 values.
    - nan_color: str or tuple, color to be used for NaN values.
    - truncate_high: float, fraction of the colormap to keep (0 to 1).

    Returns:
    - new_cmap: A colormap with modified 0 and NaN colors, and truncated upper range.
    """
    base_cmap = colormaps[cmap_name]
    truncated_cmap = base_cmap(np.linspace(0, truncate_high, base_cmap.N))
    modified_cmap = mcolors.ListedColormap(truncated_cmap)
    modified_cmap.colors[0] = mcolors.to_rgba(zero_color)

    # Set NaN color
    modified_cmap.set_bad(color=nan_color)

    return modified_cmap


class HeatmapGenerator:
    def __init__(self, media_type: list) -> None:
        self.points = {
            "LISTENING": 0.67,
            "READING": 1 / 350,
            "ANIME": 13,
            "READTIME": 0.67,
            "VN": 1 / 350,
            "MANGA": 0.25,
            "PAGE": 1,
        }
        self.media_type = media_type
        self.media_type = [s.upper() for s in self.media_type]

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the data and filter by media type
        """
        df["created_at"] = pd.to_datetime(df["created_at"], format="ISO8601")

        # Split the media_type column to remove prefixes
        if df["media_type"].str.contains(".").all():
            df["media_type"] = df["media_type"].str.split(".").str[1]
        else:
            logging.warning(
                "Logging format has changed. Please update the code to handle the new format."
            )
        if "ALL" not in self.media_type:
            df = df[df["media_type"].isin(self.media_type)]

        return df

    def calculate_points(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate the points column
        """
        return df["media_type"].map(self.points) * df["amount"]

    def create_heatmap_df(self, df: pd.DataFrame) -> dict:
        """
        Create a dictionary of heatmap dataframes, one for each year
        """
        df["points"] = self.calculate_points(df)
        df["week"] = df["created_at"].dt.isocalendar().week
        df["day"] = df["created_at"].dt.weekday
        df["year"] = df["created_at"].dt.year

        heatmap_data = {}
        for year, group in df.groupby("year"):
            year_df = group.pivot_table(
                index="day", columns="week", values="points", aggfunc="sum"
            )

            # Fill in missing weeks and days with NaN
            for i in range(1, 53):
                if i not in year_df.columns:
                    year_df[i] = np.nan
            for i in range(7):
                if i not in year_df.index:
                    year_df.loc[i] = np.nan
            year_df = year_df.sort_index(axis=1).sort_index(axis=0)
            heatmap_data[year] = year_df

        return heatmap_data

    @staticmethod
    def plot_multiple_heatmaps(
        heatmap_data: dict, output: str, cmap: str = "Greens"
    ) -> None:
        """
        Plot multiple heatmaps, one for each year
        """
        num_years = len(heatmap_data)
        # Reverse the colormap by appending '_r'
        cmap = modify_cmap(cmap + "_r", zero_color="#222222", nan_color="#222222")

        fig, axes = plt.subplots(nrows=num_years, ncols=1, figsize=(12, 2 * num_years))

        # If there's only one year, `axes` is not a list, so we make it a list for consistency
        if num_years == 1:
            axes = [axes]

        for ax, (year, df) in zip(axes, heatmap_data.items()):
            heatmap = sns.heatmap(
                df,
                cmap=cmap,
                linewidths=1.5,
                linecolor="#2c2c2d",
                cbar=False,  # Disable the default colorbar
                square=True,
                ax=ax,
            )
            ax.set_facecolor("#2c2c2d")
            ax.set_title(f"Immersion Heatmap - {year}", color="white")
            ax.axis("off")

        # Add a colorbar with a thinner width
        cbar = fig.colorbar(
            heatmap.get_children()[0],
            ax=axes,
            orientation="vertical",
            fraction=0.025,
            ticks=[],
            pad=0.02,
            aspect=10,
        )

        cbar.outline.set_visible(False)  # Hide the border outline
        plt.gcf().set_facecolor("#2c2c2d")
        plt.savefig(output, bbox_inches="tight")


@click.command()
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to the immersion logs file. If not provided, the program will search in the ./data directory.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(),
    required=True,
    help="Path to save the heatmap.",
)
@click.option(
    "--cmap",
    "selected_cmap",
    type=click.Choice(["Greens", "Blues", "Reds", "Purples", "Oranges"]),
    default="Greens",
    help="Color map for the heatmap. Default is Greens.",
)
@click.option(
    "--media",
    "-m",
    "media_type",
    default="ALL",
    help="Media type to include in the heatmap. Choose from LISTENING, READING, ANIME, READTIME, VN, MANGA, PAGE. Default is ALL.", # noqa
)
def run(input_path, output_path, selected_cmap, media_type):
    """
    Main function to generate a heatmap from immersion logs.
    """
    media_type = [media_type]
    generator = HeatmapGenerator(media_type=media_type)
    # Determine the input file
    if not input_path:
        current_dir = os.path.dirname(os.path.realpath(__file__))
        data_dir = os.path.join(current_dir, "data")
        if os.path.exists(data_dir) and len(os.listdir(data_dir)) == 1:
            input_path = os.path.join(data_dir, os.listdir(data_dir)[0])
        else:
            click.echo(
                "No input file found in the ./data directory, please provide an input path."
            )
            return

    # Read and clean the data, then create and plot the heatmap
    df = pd.read_csv(input_path)
    df = generator.clean_data(df)
    heatmap_data = generator.create_heatmap_df(df)
    generator.plot_multiple_heatmaps(heatmap_data, output_path, cmap=selected_cmap)
    click.echo(f"Heatmap saved to {output_path}")


if __name__ == "__main__":
    run()
