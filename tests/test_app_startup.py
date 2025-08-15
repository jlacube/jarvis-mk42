
import unittest
import subprocess
import time
import os

class TestAppStartup(unittest.TestCase):
    def test_app_starts_successfully(self):
        """
        Tests that the application starts up without errors.
        """
        process = None
        try:
            # Start the application as a subprocess using the virtual environment's Python
            python_exe = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.venv', 'Scripts', 'python.exe')
            process = subprocess.Popen(
                [python_exe, 'app.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=os.environ.copy(),
                cwd=os.path.dirname(os.path.dirname(__file__))
            )

            # Wait for a few seconds to see if any errors occur
            time.sleep(5)

            # Check if the process is still running (should be, if successful)
            return_code = process.poll()
            
            if return_code is not None:
                # Process terminated, check why
                stdout_output, stderr_output = process.communicate()
                self.fail(f"Application process terminated unexpectedly with code {return_code}. "
                         f"Stderr: {stderr_output}, Stdout: {stdout_output}")
            
            # If we get here, the process is still running, which means success
            print("Application started successfully and is running")

        finally:
            # Ensure the process is terminated after the test
            if process and process.poll() is None:
                process.terminate()
                process.wait()

if __name__ == '__main__':
    unittest.main()
