import pytest
import pandas as pd
import re
import matplotlib
# Use a non-interactive backend for testing to avoid Tkinter dependency
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from tools.plotting import plot_tool, generate_plot

@pytest.mark.asyncio
async def test_plot_tool_with_markdown_table():
    """Test that plot_tool can generate a plot from a markdown table."""
    # Create a simple markdown table for testing with format that matches pandas read_table
    markdown_table = """
Month,Sales
Jan,100
Feb,150
Mar,200
Apr,120
May,180
    """
    
    # Test different plot types
    plot_types = ["line", "bar", "scatter"]
    
    for plot_type in plot_types:
        result = await plot_tool.ainvoke({
            "data": markdown_table,
            "plot_type": plot_type,
            "title": f"Test {plot_type.capitalize()} Plot",
            "x_label": "Month",
            "y_label": "Sales"
        })
        
        # We can't easily test the visual output in an automated test,
        # but we can verify that the function returns success
        assert result == "ok", f"plot_tool should return 'ok' for {plot_type} plot"

@pytest.mark.asyncio
async def test_plot_tool_with_dict_data():
    """Test that plot_tool can generate a plot from dictionary data."""
    # Create data in CSV format
    dict_data = """x,y
1,10
2,20
3,15
4,30
5,25"""
    
    result = await plot_tool.ainvoke({
        "data": dict_data,
        "plot_type": "line",
        "title": "Test Dictionary Plot",
        "x_label": "X Values",
        "y_label": "Y Values"
    })
    
    assert result == "ok", "plot_tool should return 'ok' for dictionary data"

def test_generate_plot_function():
    """Test the underlying generate_plot function directly."""
    # Create a test DataFrame
    df = pd.DataFrame({
        'x': [1, 2, 3, 4, 5],
        'y': [10, 20, 15, 30, 25]
    })
    
    # Test different plot types
    plot_types = ["line", "bar", "scatter", "histogram"]
    
    for plot_type in plot_types:
        plt_obj = generate_plot(
            data=df,
            plot_type=plot_type,
            title=f"Test {plot_type.capitalize()} Plot",
            x_label="X Values",
            y_label="Y Values"
        )
        
        # Verify that a matplotlib figure was returned
        assert plt_obj is not None, f"generate_plot should return a plot object for {plot_type}"
        
        # Clean up the plot to avoid memory issues
        plt.close()

@pytest.mark.asyncio
async def test_plot_tool_error_handling():
    """Test that plot_tool handles errors gracefully."""
    # Test with invalid data
    invalid_data = "This is not valid data for plotting"
    
    result = await plot_tool.ainvoke({
        "data": invalid_data,
        "plot_type": "line",
        "title": "This Should Fail",
        "x_label": "X",
        "y_label": "Y"
    })
    
    assert result == "ko", "plot_tool should return 'ko' for invalid data"
    
    # Test with invalid plot type
    valid_data = "{'x': [1, 2, 3], 'y': [10, 20, 30]}"
    
    result = await plot_tool.ainvoke({
        "data": valid_data,
        "plot_type": "invalid_type",
        "title": "This Should Fail",
        "x_label": "X",
        "y_label": "Y"
    })
    
    assert result == "ko", "plot_tool should return 'ko' for invalid plot type"
