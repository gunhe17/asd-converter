from ASDconverter.device.realsense import Realsense
from ASDconverter.device.tobii import Tobii
from ASDconverter.device.played import Played
from ASDconverter.device.user import User
from ASDconverter.filter.filter import Filter
from ASDconverter.matcher.matcher import Matcher

class Converter:
    def __init__(self):
        self.realsense = Realsense()
        self.tobii = Tobii()
        self.user = User()
        self.played = Played()

        self.filter = Filter()
        self.matcher = Matcher()

    def convert(self, input_dir, output_dir):
        self.realsense.convert(input_dir, output_dir)
        self.tobii.convert(input_dir, output_dir)
        self.user.convert(input_dir, output_dir)
        self.played.convert(input_dir, output_dir)

        self.filter.filter_frames(output_dir)

        self.matcher.match_frames(output_dir)


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