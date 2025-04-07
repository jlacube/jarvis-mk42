import io
from typing import Union

import chainlit as cl

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from langchain_core.tools import tool


def generate_plot(data, plot_type='line', title='Data Visualization', x_label='X-axis', y_label='Y-axis'):
    """
    Generate an interactive plot using matplotlib and seaborn.

    Args:
        data (pd.DataFrame or dict): Input data for plotting
        plot_type (str): Type of plot (line, bar, scatter, histogram)
        title (str): Plot title
        x_label (str): X-axis label
        y_label (str): Y-axis label

    Returns:
        plt.Figure: Matplotlib figure object
    """
    # Set seaborn style for enhanced aesthetics
    #sns.set_theme(style="whitegrid")
    sns.set_theme(style="darkgrid")

    # Create a new figure
    plt.figure(figsize=(10, 6))

    # Convert dict to DataFrame if needed
    if isinstance(data, dict):
        data = pd.DataFrame(data)

    # Plot based on type
    try:
        if plot_type == 'line':
            sns.lineplot(x=data.columns[0],y=data.columns[1],data=data)
        elif plot_type == 'bar':
            sns.barplot(x=data.columns[0],y=data.columns[1],data=data)
        elif plot_type == 'scatter':
            sns.scatterplot(x=data.columns[0],y=data.columns[1],data=data)
        elif plot_type == 'histogram':
            sns.histplot(x=data.columns[0],y=data.columns[1],data=data)
        else:
            raise ValueError(f"Unsupported plot type: {plot_type}")

        # Set plot details
        plt.title(title, fontsize=15)
        plt.xlabel(x_label, fontsize=12)
        plt.ylabel(y_label, fontsize=12)
        plt.tight_layout()

        return plt

    except Exception as e:
        print(f"Error generating plot: {e}")
        return None


@tool
async def plot_tool(data:str, plot_type:str = 'line', title:str = 'Sample Line Plot', x_label:str = 'X Values', y_label:str = 'Y Values'):
    """
    Call this tool for plot generation

    :param data: Input data for plotting, Markdown table, dict or pd.DataFrame
    :param plot_type: Type of plot (line, bar, scatter, histogram)
    :param title: Plot title
    :param x_label: X-axis label
    :param y_label: Y-axis label
    :return ok if the tool worked, ko otherwise
    """

    plot = generate_plot(
        data=data,
        plot_type=plot_type,
        title=title,
        x_label=x_label,
        y_label=y_label
    )

    if plot:
        # Save plot to a file
        buf = io.BytesIO()
        plot.savefig(buf, format='png')
        buf.seek(0)

        # Send plot as an image in Chainlit
        await cl.Message(
            content="Here's your generated plot!",
            elements=[cl.Image(name="plot.png", display="inline", content=buf.read())]
        ).send()
        return "ok"
    else:
        return "ko"