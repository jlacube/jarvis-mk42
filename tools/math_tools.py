import sympy
import numpy as np  # Although not directly exposed, sympy might use it internally
import scipy.optimize # Kept for potential future extensions, but nsolve is preferred
import math

from langchain_core.tools import tool
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, function_exponentiation
)
from sympy.utilities.lambdify import lambdify


@tool
async def calculator_tool(expression: str) -> str:
    """
    Performs calculations including arithmetic, symbolic math, and equation solving
    using the SymPy library.

    Args:
        expression: A string containing the mathematical expression or equation to evaluate.
                    The expression should use standard Python/SymPy syntax.
                    Examples:
                      '1 + 2 * 3 / 4'
                      'sqrt(16)'
                      'sin(pi/2) + cos(0)'
                      'E**(I*pi)' # Euler's identity
                      'simplify(cos(x)**2 + sin(x)**2)'
                      'expand((x+y)**3'
                      'factor(x**2 - 2*x + 1)'
                      'diff(x**4 / tan(x), x)'
                      'integrate(x**2 * exp(x), x)' # Indefinite integral
                      'integrate(1/(x**2+1), (x, -oo, oo))' # Definite integral
                      'limit(sin(x)/x, x, 0)'
                      'solve(Eq(x**2, 9), x)' # Solve equation symbolically
                      'solve(x**2 + 2*x + 5, x)' # Solve polynomial for roots
                      'solve([Eq(x + y, 5), Eq(x - y, 1)], [x, y])' # Solve system of linear equations
                      'nsolve(Eq(cos(x), x), x, 0.5)' # Solve equation numerically (requires initial guess)
                      'N(pi, 50)' # Evaluate pi to 50 decimal places
                      'log(1000, 10)' # Log base 10
                      'isprime(17)'
                      'factorial(5)'

    Returns:
        A string representing the result of the calculation or an error message.
    """
    try:
        # 1. Preprocessing (SymPy parser handles most cases like ^ vs **)
        # expression = expression.replace('^', '**') # Usually not needed with parse_expr

        # 2. Define allowed functions, constants, and classes for parsing
        # Using SymPy's versions ensures compatibility within the symbolic framework.
        local_dict = {
            # Solvers
            "solve": sympy.solve,
            "nsolve": sympy.nsolve, # Numerical solver

            # Equation/Relationals
            "Eq": sympy.Eq, "Ne": sympy.Ne, "Lt": sympy.Lt, "Le": sympy.Le, "Gt": sympy.Gt, "Ge": sympy.Ge,

            # Calculus
            "diff": sympy.diff, "Derivative": sympy.Derivative,
            "integrate": sympy.integrate, "Integral": sympy.Integral,
            "limit": sympy.limit, "Limit": sympy.Limit,

            # Simplification/Manipulation
            "simplify": sympy.simplify, "expand": sympy.expand, "factor": sympy.factor,
            "collect": sympy.collect, "cancel": sympy.cancel, "apart": sympy.apart,
            "trigsimp": sympy.trigsimp, "expand_trig": sympy.expand_trig,

            # Evaluation
            "N": sympy.N, "evalf": sympy.N, # Numerical evaluation

            # Basic Functions (Trigonometric, Hyperbolic, Exponential, Logarithmic)
            "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
            "asin": sympy.asin, "acos": sympy.acos, "atan": sympy.atan, "atan2": sympy.atan2,
            "sinh": sympy.sinh, "cosh": sympy.cosh, "tanh": sympy.tanh,
            "asinh": sympy.asinh, "acosh": sympy.acosh, "atanh": sympy.atanh,
            "log": sympy.log, "ln": sympy.log, # ln is alias for natural log
            "exp": sympy.exp,
            "sqrt": sympy.sqrt,
            "Abs": sympy.Abs, "abs": sympy.Abs, # abs is alias
            "sign": sympy.sign,
            "conjugate": sympy.conjugate,
            "re": sympy.re, "im": sympy.im,
            "arg": sympy.arg,

            # Constants
            "pi": sympy.pi,
            "E": sympy.E, # Euler's number
            "I": sympy.I, # Imaginary unit
            "oo": sympy.oo, # Infinity
            "zoo": sympy.zoo, # Complex infinity
            "nan": sympy.nan, # Not a number

            # Combinatorics
            "factorial": sympy.factorial, "binomial": sympy.binomial,

            # Number Theory
            "gcd": sympy.gcd, "lcm": sympy.lcm, "isprime": sympy.isprime,
            "prime": sympy.prime, "primerange": sympy.primerange, "nextprime": sympy.nextprime,

            # Logic
            "And": sympy.And, "Or": sympy.Or, "Not": sympy.Not, "Xor": sympy.Xor,
            "true": sympy.true, "false": sympy.false,

            # Matrix operations (Basic)
            "Matrix": sympy.Matrix,
            "eye": sympy.eye,
            "zeros": sympy.zeros,
            "ones": sympy.ones,
            "diag": sympy.diag,

            # Note: Exposing full numpy (np) or scipy is generally avoided
            # here to rely on SymPy's integrated environment, but specific
            # functions could be added carefully if needed.
        }

        # 3. Set up parsing transformations for flexibility
        # Allows implicit multiplication ('2x'), function exponentiation ('sin**2(x)') etc.
        transformations = standard_transformations + (implicit_multiplication_application, function_exponentiation)

        # 4. Parse the expression using SymPy's parser
        # evaluate=True attempts to perform basic simplifications and evaluations during parsing.
        # For example, '1+2' will become sympy.Integer(3) directly.
        parsed_expr = parse_expr(expression, local_dict=local_dict, transformations=transformations, evaluate=True)

        # 5. Evaluate the parsed expression if it's evaluatable
        # Check if it still contains symbols. If not, evaluate numerically.
        # Results from solve(), diff(), integrate() might be lists or symbolic expressions.
        result = parsed_expr

        # Attempt numerical evaluation if the result has no free symbols (variables)
        # and is not already a specific type like list (from solve) or bool (from isprime)
        if not isinstance(result, (list, tuple, dict, bool)) and not result.free_symbols:
             # Use N() for numerical evaluation to handle potential symbolic constants like pi, E
             # Use .evalf() for potentially higher precision control if needed later
            try:
                # Check for specific types that shouldn't be N'd directly (like Matrix)
                if not isinstance(result, (sympy.Matrix,)) :
                     evaluated_result = sympy.N(result)
                     # Only update if N() doesn't fail or return a symbolic type again
                     if not isinstance(evaluated_result, (sympy.Expr, sympy.Basic)) or not evaluated_result.free_symbols:
                         result = evaluated_result
            except (TypeError, ValueError, NotImplementedError):
                # If N() fails, keep the symbolic result (e.g., unevaluated Integral/Derivative)
                pass


        # 6. Convert the final result to a string
        return str(result)

    # 7. Error Handling
    except (SyntaxError, TypeError, ValueError) as e:
        return f"Error: Invalid expression, syntax, or function argument - {type(e).__name__}: {e}"
    except sympy.SympifyError as e:
        return f"Error: Could not parse expression - {e}"
    except NotImplementedError as e:
        # Specific SymPy functions might raise this if a feature is not implemented
        return f"Error: Calculation or feature not implemented in SymPy - {e}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except AttributeError as e:
        # Catches errors like calling a method on an inappropriate object type
        return f"Error: Invalid operation or attribute - {e}"
    except Exception as e:
        # Catch any other unexpected errors during parsing or evaluation
        return f"An unexpected error occurred: {type(e).__name__} - {e}"

# Example usage (for demonstration):
# print(f"'1+2*3': {calculate('1+2*3')}")
# print(f"'sin(pi/2)': {calculate('sin(pi/2)')}")
# print(f"'diff(x**3, x)': {calculate('diff(x**3, x)')}")
# print(f"'solve(Eq(x**2, 4), x)': {calculate('solve(Eq(x**2, 4), x)')}")
# print(f"'nsolve(cos(x) - x, x, 1)': {calculate('nsolve(cos(x) - x, x, 1)')}")
# print(f"'integrate(1/x, x)': {calculate('integrate(1/x, x)')}")
# print(f"'N(E, 20)': {calculate('N(E, 20)')}")
# print(f"'1/0': {calculate('1/0')}")
# print(f"'invalid_syntax***': {calculate('invalid_syntax***')}")
# print(f"'Matrix([[1, 2], [3, 4]])**2': {calculate('Matrix([[1, 2], [3, 4]])**2')}")
# print(f"'solve(Eq(exp(x), 0), x)': {calculate('solve(Eq(exp(x), 0), x)')}") # Expected: []
