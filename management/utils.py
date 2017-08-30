#!/usr/bin/env python3
from plumbum import cli


class M(cli.Application):
    subcommands = {}
    
    @classmethod
    def print_commands(cls, root=None, indent=0):
        if root is None:
            root = cls.subcommands
        for name, (app, sub_cmds) in root.items():
            print(" "*indent, "Name:", name, "App:", app._NAME)
            cls.print_commands(root=sub_cmds, indent=indent+2)
            
    @classmethod
    def command(cls, name=None):
        postfix = name
        def decorator(method):
            if postfix is None:
                name = method.__name__
            else:
                name = postfix
            mod = method.__module__
            if mod.startswith('management'):
                mod = mod[len('management'):]
                mod = mod.lstrip('.')
            if mod == '__main__':
                full_name = name
            else:
                full_name = mod+'.'+name
                
            #print("Registering command", full_name)
            
            app = cls
            subcmds = cls.subcommands
            for sub in full_name.split('.')[:-1]:
                if sub not in subcmds:
                    #print("  Defining subcommand", sub)
                    sub_app = type(sub+'App', (cli.Application,),{})
                    sub_app = app.subcommand(sub)(sub_app)
                    subcmds[sub] = (sub_app, {})
                else:
                    #print("  Subcommand defined", sub)
                    pass
                    
                app, subcmds = subcmds[sub]
            
            #print("* Defining subcommand", name)
            
            def main(self, *args):
                method(*args)
                
            newclass = type(name+'App', (cli.Application,),{"main": main})
            newclass = app.subcommand(name)(newclass)
            return method
        
        return decorator
