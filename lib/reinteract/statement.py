#!/usr/bin/python

import copy
import sys

import rewrite
from custom_result import CustomResult

_DEFINE_GLOBALS = compile("""
global reinteract_output, reinteract_print
def reinteract_output(*args):
   __reinteract_statement.do_output(*args)
def reinteract_print(*args):
   __reinteract_statement.do_print(*args)
""", __name__, 'exec')

# A wrapper so we don't have to trap all exceptions when running statement.Execute
class ExecutionError(Exception):
    def __init__(self, cause, traceback):
        self.cause = cause
        self.traceback = traceback

    def __str__(self):
        return "ExecutionError: " + str(self.cause)

class Statement:
    def __init__(self, text, parent = None):
        self.__text = text
        self.__globals = None
        self.result_scope = None
        self.results = None

        # May raise SyntaxError
        self.__compiled, self.__mutated = rewrite.rewrite_and_compile(self.__text)

        self.set_parent(parent)

    def get_globals(self):
        if self.__globals == None:
            if self.__parent != None:
                self.__globals = self.__parent.get_globals()
            else:
                self.__globals = { '__builtins__': __builtins__ }
                exec _DEFINE_GLOBALS in self.__globals

        return self.__globals
        
    def set_parent(self, parent):
        self.__parent = parent
        self.__globals = None
        
    def get_result_scope(self):
        return self.result_scope

    def do_output(self, *args):
        if len(args) == 1:
            arg = args[0]
            
            if args[0] == None:
                return
            elif isinstance(args[0], CustomResult):
                self.results.append(args[0])
            else:
                self.results.append(repr(args[0]))
        else:
            self.results.append(repr(args))

    def do_print(self, *args):
        self.results.append(" ".join(map(str, args)))

    def execute(self):
        global_scope = self.get_globals()

        if self.__parent:
            local_scope = copy.copy(self.__parent.result_scope)
        else:
            local_scope = {}

        for mutation in self.__mutated:
            if isinstance(mutation, tuple):
                variable, method = mutation
            else:
                variable = mutation

            local_scope[variable] = copy.copy(local_scope[variable])

        self.results = []
        global_scope['__reinteract_statement'] = self
        try:
            exec self.__compiled in global_scope, local_scope
        except:
            self.results = None
            _, cause, traceback = sys.exc_info()
            raise ExecutionError(cause, traceback)
        finally:
            global_scope['__reinteract_statement'] = None

        self.result_scope = local_scope

if __name__=='__main__':
    def expect(actual,expected):
        if actual != expected:
            raise AssertionError("Got: '%s'; Expected: '%s'" % (actual, expected))

    def expect_result(text, result):
        s = Statement(text)
        s.execute()
        expect(s.results[0], result)

    # A bare expression should give the repr of the expression
    expect_result("'a'", repr('a'))
    expect_result("1,2", repr((1,2)))

    # Print, on the other hand, gives the string form of the expression
    expect_result("print 'a'", 'a')

    # Test that we copy a variable before mutating it (when we can detect
    # the mutation)
    s1 = Statement("b = [0]")
    s1.execute()
    s2 = Statement("b[0] = 1", parent=s1)
    s2.execute()
    s3 = Statement("b[0]", parent = s2)
    s3.execute()
    expect(s3.results[0], "1")
    
    s2a = Statement("b[0]", parent=s1)
    s2a.execute()
    expect(s2a.results[0], "0")