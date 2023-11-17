class Person:
    def __init__(self, name):
        self.name = name

    def say_name(self):
        print(f"My name is {self.name}")


class FormalPerson(Person):
    pass
