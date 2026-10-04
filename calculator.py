def add(x, y):
    return x + y

def subtract(x, y):
    return x - y

def multiply(x, y):
    return x * y

def divide(x, y):
    if y == 0:
        return "Error: Division by zero is undefined."
    return x / y

def modulus(x, y):
    if y == 0:
        return "Error: Division by zero is undefined."
    return x % y

def power(x, y):
    return x ** y

def calculator():
    print("=== Simple Arithmetic Calculator ===")
    print("Operations:")
    print("  + : Addition")
    print("  - : Subtraction")
    print("  * : Multiplication")
    print("  / : Division")
    print("  % : Modulus")
    print("  ^ : Power")
    print("Type 'q' to quit.")

    while True:
        choice = input("\nEnter operation (+, -, *, /, %, ^) or 'q' to exit: ").strip()

        if choice.lower() == 'q':
            print("Exiting calculator. Goodbye!")
            break

        if choice not in ('+', '-', '*', '/', '%', '^'):
            print("Invalid operation. Please choose from +, -, *, /, %, ^.")
            continue

        try:
            num1 = float(input("Enter first number: "))
            num2 = float(input("Enter second number: "))
        except ValueError:
            print("Invalid input! Please enter numeric values.")
            continue

        if choice == '+':
            result = add(num1, num2)
        elif choice == '-':
            result = subtract(num1, num2)
        elif choice == '*':
            result = multiply(num1, num2)
        elif choice == '/':
            result = divide(num1, num2)
        elif choice == '%':
            result = modulus(num1, num2)
        elif choice == '^':
            result = power(num1, num2)

        print(f"Result: {num1} {choice} {num2} = {result}")

if __name__ == "__main__":
    calculator()
