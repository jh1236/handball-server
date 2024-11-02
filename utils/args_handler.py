import argparse

_parser = argparse.ArgumentParser(prog='start.py', description='Start the SUSS server')  
_parser.add_argument("-d", "--debug", action="store_true")
_parser.add_argument("-nd", "--no-debug", action="store_false", dest="debug")
_parser.set_defaults(debug=True)
_parser.add_argument("-p", "--port", type=int, default=-1)
_parser.add_argument("-db", "--database", default="sqlite:///database.db")
_parser.add_argument("-l", "--log", default="INFO")

args = _parser.parse_args()