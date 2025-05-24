import io
import logging
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
        logging.error(f"Error generating plot: {e}")
        return None


@tool
async def plot_tool(data:str, plot_type:str = 'line', title:str = 'Sample Line Plot', x_label:str = 'X Values', y_label:str = 'Y Values'):
    """
    Generates and displays a data visualization plot based on the provided data.
    
    This tool creates various types of plots (line, bar, scatter, histogram) from
    structured data and sends the visualization to the user in the chat interface.
    
    Args:
        data (str): Input data for plotting in the form of a Markdown table, 
                   dictionary, or pandas DataFrame string representation.
                   The data should have at least two columns for X and Y values.
        plot_type (str, optional): Type of plot to generate. Options include:
                                   'line', 'bar', 'scatter', 'histogram'.
                                   Defaults to 'line'.
        title (str, optional): Title to display on the plot.
                              Defaults to 'Sample Line Plot'.
        x_label (str, optional): Label for the X-axis.
                                Defaults to 'X Values'.
        y_label (str, optional): Label for the Y-axis.
                                Defaults to 'Y Values'.
                                
    Returns:
        str: "ok" if the plot was successfully generated and sent,
             "ko" if there was an error in plot generation.
             
    Implementation Details:
        - Uses matplotlib and seaborn for plot generation
        - Converts input data to the appropriate format
        - Generates the plot with specified parameters
        - Sends the plot as an image to the chat interface
        
    Example:
        result = await plot_tool(
            data="| Month | Sales |\n|-------|-------|\n| Jan | 100 |\n| Feb | 150 |\n| Mar | 200 |",
            plot_type="bar",
            title="Quarterly Sales",
            x_label="Month",
            y_label="Sales ($)"
        )
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

