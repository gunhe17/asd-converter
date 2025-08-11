import os
from pathlib import Path

from ASDconverter.device.realsense import Realsense
from ASDconverter.device.tobii import Tobii


class Converter:
    def __init__(self):
        # realsense
        self.realsense = Realsense()
        # tobii
        self.tobii = Tobii()


    def convert(self, input_dir: str, output_dir: str):
        # RealSense 변환
        # self.realsense.convert(input_dir, output_dir)
        
        # Tobii 변환
        self.tobii.convert(input_dir, output_dir)


def argparser():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path")
    parser.add_argument("--output_path")

    return parser.parse_args()
    
def main():
    args = argparser()
    
    converter = Converter()
    converter.convert(args.input_path, args.output_path)

if __name__ == "__main__":
    main()