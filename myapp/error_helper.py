class ErrorExplainer:
    def explain(self, error_message):
        error = str(error_message).lower()
        
        # Colon error
        if 'invalid syntax' in error and ':' in error:
            return {
                'message': '❌ You forgot to add colon (:) !',
                'fix': 'Add colon (:) at the end of line',
                'example': 'if x > 5:    # Correct\nif x > 5     # Wrong'
            }
        
        # Indentation error
        elif 'indentation' in error:
            return {
                'message': '❌ Problem with spaces!',
                'fix': 'Press Tab key or add 4 spaces',
                'example': 'def hello():\n    print("Hi")'
            }
        
        # Variable not defined
        elif 'name' in error and 'not defined' in error:
            return {
                'message': '❌ This variable does not exist!',
                'fix': 'Define the variable first',
                'example': 'x = 10\nprint(x)'
            }
        
        # Zero division
        elif 'division by zero' in error:
            return {
                'message': '❌ Cannot divide by zero!',
                'fix': 'Make sure denominator is not zero',
                'example': 'if y != 0:\n    result = x / y'
            }
        
        # Default
        else:
            return {
                'message': '🤔 Something went wrong',
                'fix': 'Check your code line by line',
                'example': 'Search the error on Google'
            }