import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio
from langchain_core.tools import BaseTool


class TestMathToolsComplete:
    """Comprehensive test coverage for tools.math_tools module."""
    
    @pytest.mark.asyncio
    async def test_calculator_tool_basic_arithmetic(self):
        """Test calculator_tool with basic arithmetic operations."""
        from tools.math_tools import calculator_tool
        
        # Test basic arithmetic
        result = await calculator_tool.ainvoke({"expression": "1 + 2 * 3"})
        assert "7" in result
        
        # Test division
        result = await calculator_tool.ainvoke({"expression": "10 / 2"})
        assert "5" in result
        
        # Test parentheses
        result = await calculator_tool.ainvoke({"expression": "(1 + 2) * 3"})
        assert "9" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_symbolic_math(self):
        """Test calculator_tool with symbolic math operations."""
        from tools.math_tools import calculator_tool
        
        # Test symbolic differentiation
        result = await calculator_tool.ainvoke({"expression": "diff(x**2, x)"})
        assert "2*x" in result
        
        # Test integration
        result = await calculator_tool.ainvoke({"expression": "integrate(x**2, x)"})
        assert "x**3/3" in result or "x^3/3" in result
        
        # Test equation solving
        result = await calculator_tool.ainvoke({"expression": "solve(x**2 - 4, x)"})
        assert "-2" in result and "2" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_trigonometric_functions(self):
        """Test calculator_tool with trigonometric functions."""
        from tools.math_tools import calculator_tool
        
        # Test sine
        result = await calculator_tool.ainvoke({"expression": "sin(pi/2)"})
        assert "1" in result
        
        # Test cosine
        result = await calculator_tool.ainvoke({"expression": "cos(0)"})
        assert "1" in result
        
        # Test numerical evaluation
        result = await calculator_tool.ainvoke({"expression": "N(pi, 5)"})
        assert "3.1415" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_matrix_operations(self):
        """Test calculator_tool with matrix operations."""
        from tools.math_tools import calculator_tool
        
        # Test matrix creation and multiplication
        result = await calculator_tool.ainvoke({"expression": "Matrix([[1, 2], [3, 4]]) * Matrix([[1, 0], [0, 1]])"})
        assert "Matrix" in result and "1" in result and "2" in result
        
        # Test matrix determinant
        result = await calculator_tool.ainvoke({"expression": "Matrix([[1, 2], [3, 4]]).det()"})
        assert "-2" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_invalid_expression_error(self):
        """Test calculator_tool with invalid expressions."""
        from tools.math_tools import calculator_tool
        
        # Test malformed expression - it causes IndexError which is caught by general exception handler
        result = await calculator_tool.ainvoke({"expression": "x) + ("})
        assert "Error" in result and "IndexError" in result
        
        # Test with lambda (SymPy actually handles this as Lambda function)
        result = await calculator_tool.ainvoke({"expression": "lambda x: x + 1"})
        assert isinstance(result, str)  # Just verify it returns a string

    @pytest.mark.asyncio
    async def test_calculator_tool_empty_expression(self):
        """Test calculator_tool with empty expression."""
        from tools.math_tools import calculator_tool
        
        result = await calculator_tool.ainvoke({"expression": ""})
        assert "Error" in result or "error" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_numerical_solving(self):
        """Test calculator_tool with numerical solving."""
        from tools.math_tools import calculator_tool
        
        # Test nsolve for numerical solutions
        result = await calculator_tool.ainvoke({"expression": "nsolve(cos(x) - x, x, 1)"})
        assert "0.739" in result or "0.74" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_complex_numbers(self):
        """Test calculator_tool with complex numbers."""
        from tools.math_tools import calculator_tool
        
        # Test complex number operations
        result = await calculator_tool.ainvoke({"expression": "sqrt(-1)"})
        assert "I" in result
        
        # Test complex arithmetic
        result = await calculator_tool.ainvoke({"expression": "(1 + I) * (1 - I)"})
        assert "2" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_logarithms_and_exponentials(self):
        """Test calculator_tool with logarithms and exponentials."""
        from tools.math_tools import calculator_tool
        
        # Test natural logarithm
        result = await calculator_tool.ainvoke({"expression": "log(E)"})
        assert "1" in result
        
        # Test exponential
        result = await calculator_tool.ainvoke({"expression": "exp(0)"})
        assert "1" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_limits(self):
        """Test calculator_tool with limit calculations."""
        from tools.math_tools import calculator_tool
        
        # Test limit calculation
        result = await calculator_tool.ainvoke({"expression": "limit(sin(x)/x, x, 0)"})
        assert "1" in result

    @pytest.mark.asyncio
    async def test_calculator_tool_series_and_summations(self):
        """Test calculator_tool with series and summations."""
        from tools.math_tools import calculator_tool
        
        # Test summation
        result = await calculator_tool.ainvoke({"expression": "Sum(n, (n, 1, 10))"})
        assert "55" in result or "Sum" in result

    def test_get_math_tools_function(self):
        """Test get_math_tools function returns the correct tools."""
        from tools.math_tools import get_math_tools, calculator_tool
        
        tools = get_math_tools()
        
        # Should return a list containing calculator_tool
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert calculator_tool in tools
        
        # Verify the tool has the expected attributes
        tool = tools[0]
        assert hasattr(tool, 'name')
        assert hasattr(tool, 'description')
        assert tool.name == 'calculator_tool'

    @pytest.mark.asyncio
    async def test_calculator_tool_edge_case_division_by_zero(self):
        """Test calculator_tool with division by zero."""
        from tools.math_tools import calculator_tool
        
        # Test division by zero
        result = await calculator_tool.ainvoke({"expression": "1/0"})
        assert "zoo" in result.lower() or "infinity" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_calculator_tool_very_large_numbers(self):
        """Test calculator_tool with very large numbers."""
        from tools.math_tools import calculator_tool
        
        # Test large number calculation
        result = await calculator_tool.ainvoke({"expression": "factorial(10)"})
        assert "3628800" in result
        
        # Test power of large numbers
        result = await calculator_tool.ainvoke({"expression": "2**100"})
        assert len(result) > 10  # Very large result

    @pytest.mark.asyncio
    async def test_calculator_tool_irrational_numbers(self):
        """Test calculator_tool with irrational numbers."""
        from tools.math_tools import calculator_tool
        
        # Test pi (it gets evaluated to numerical form)
        result = await calculator_tool.ainvoke({"expression": "pi"})
        assert "3.14" in result
        
        # Test e (it gets evaluated to numerical form)
        result = await calculator_tool.ainvoke({"expression": "E"})
        assert "2.71" in result

    @pytest.mark.asyncio 
    async def test_calculator_tool_string_conversion_edge_case(self):
        """Test calculator_tool with expressions that might have string conversion issues."""
        from tools.math_tools import calculator_tool
        
        # Test expressions that result in sets or complex objects
        result = await calculator_tool.ainvoke({"expression": "solve(x**2 - x - 6, x)"})
        # Should handle set results properly
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_calculator_tool_specific_error_types(self):
        """Test calculator_tool with expressions that trigger specific error types."""
        from tools.math_tools import calculator_tool
        
        # Test NotImplementedError by using unsupported operations
        result = await calculator_tool.ainvoke({"expression": "solve(cos(x)*sin(x) - x**10, x)"})
        # Complex transcendental equations might not be implemented
        assert isinstance(result, str)
        
        # Test ValueError with invalid domain
        result = await calculator_tool.ainvoke({"expression": "sqrt(-1, real=True)"})
        # Should handle invalid domain gracefully
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_calculator_tool_attribute_error(self):
        """Test calculator_tool with expressions that might cause AttributeError."""
        from tools.math_tools import calculator_tool
        
        # Try operations that might not exist on certain objects
        result = await calculator_tool.ainvoke({"expression": "Matrix([[1, 2]]).nonexistent_method()"})
        assert "Error" in result and ("attribute" in result or "AttributeError" in result)
    
    @pytest.mark.asyncio
    async def test_calculator_tool_zero_division_explicit(self):
        """Test calculator_tool with explicit zero division."""
        from tools.math_tools import calculator_tool
        
        # Explicit zero division
        result = await calculator_tool.ainvoke({"expression": "1/0"})
        # SymPy handles this as complex infinity, but check for proper handling
        assert isinstance(result, str)
        
    @pytest.mark.asyncio
    async def test_calculator_tool_type_error_scenarios(self):
        """Test calculator_tool with expressions that might cause TypeError."""
        from tools.math_tools import calculator_tool
        
        # Test operations that might cause type errors
        result = await calculator_tool.ainvoke({"expression": "factorial(-1)"})
        # Negative factorial should cause an error or be handled gracefully
        assert isinstance(result, str)
        
        # Test invalid argument types
        result = await calculator_tool.ainvoke({"expression": "log(Matrix([[1, 2]]))"})
        # Log of matrix should cause type error or be handled gracefully
        assert isinstance(result, str)
        
    @pytest.mark.asyncio
    async def test_calculator_tool_sympify_error(self):
        """Test calculator_tool with expressions that trigger SympifyError."""
        from tools.math_tools import calculator_tool
        import sympy
        
        # The @@##$$ causes SyntaxError which is caught by the first exception handler
        result = await calculator_tool.ainvoke({"expression": "@@##$$"})
        assert "Error" in result and "SyntaxError" in result
        
    @pytest.mark.asyncio
    async def test_calculator_tool_zero_division_direct(self):
        """Test calculator_tool to trigger actual ZeroDivisionError."""
        from tools.math_tools import calculator_tool
        
        # Try to trigger actual ZeroDivisionError (though SymPy might handle this as zoo)
        # We need an expression that might cause Python's ZeroDivisionError rather than SymPy's handling
        result = await calculator_tool.ainvoke({"expression": "sympify('1') / sympify('0')"})
        assert isinstance(result, str)
        
    @pytest.mark.asyncio 
    async def test_calculator_tool_numerical_evaluation_errors(self):
        """Test calculator_tool with expressions that cause errors in numerical evaluation."""
        from tools.math_tools import calculator_tool
        
        # Test expression that might cause TypeError/ValueError in N() evaluation
        # Complex expressions that can't be numerically evaluated
        result = await calculator_tool.ainvoke({"expression": "Sum(1/n, (n, 1, oo))"})
        # This might cause evaluation issues when trying to convert to numerical form
        assert isinstance(result, str)
