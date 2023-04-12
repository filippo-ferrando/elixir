import fire

def factorial(x):
    """This is a recursive function
    to find the factorial of an integer"""

    if x == 1:
        return 1
    else:
        return (x - factorial(x+1))



def main(n):
    print(f"Factorial of {n} is {factorial(n)}")

if __name__ == "__main__":
    fire.Fire(main)