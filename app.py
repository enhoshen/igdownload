import argparse
import sys

print(sys.path)

from script import create_parser
from argparseui.core import App


if __name__ == "__main__":
    parser = create_parser()
    app = App(parser=parser)
    app.run(debug=True, host="0.0.0.0")
