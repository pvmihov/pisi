import commands
import checkers

class Task:
    command : commands.Command
    checker : checkers.Checker

    def __init__(self, command : commands.Command, checker : checkers.Checker):
        self.command = command
        self.checker = checker

    def handle_result(self, result):
        if self.checker.test_result(result):
            self.command.do_command()

class HoldTask(Task):
    doing_comm : bool

    def __init__(self, command : commands.Command, checker : checkers.Checker):
        super().__init__(command,checker)
        self.doing_comm = False

    def handle_result(self, result):
        res = self.checker.test_result(result)
        if res and not self.doing_comm:
            self.command.start_command()
            self.doing_comm = True
        elif not res and self.doing_comm:
            self.command.end_command()
            self.doing_comm = False


class ArgumentTask(Task):
    
    def __init__(self, command : commands.ArgumentCommand, checker : checkers.ArgumentChecker):
        super().__init__(command,checker)
    
    def handle_result(self, result):
        argument = self.checker.test_result(result)
        if argument == False: return
        self.command.do_command(argument)
