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
        print("=== ASD Converter 시작 ===")
        print(f"입력 디렉토리: {input_dir}")
        print(f"출력 디렉토리: {output_dir}")
        
        print("\n[1/6] Realsense 데이터 변환 시작...")
        self.realsense.convert(input_dir, output_dir)
        print("[1/6] Realsense 데이터 변환 완료")
        
        print("\n[2/6] Tobii 데이터 변환 시작...")
        self.tobii.convert(input_dir, output_dir)
        print("[2/6] Tobii 데이터 변환 완료")
        
        print("\n[3/6] User 데이터 변환 시작...")
        self.user.convert(input_dir, output_dir)
        print("[3/6] User 데이터 변환 완료")
        
        print("\n[4/6] Played 데이터 변환 시작...")
        self.played.convert(input_dir, output_dir)
        print("[4/6] Played 데이터 변환 완료")

        print("\n[5/6] 프레임 필터링 시작...")
        self.filter.filter_frames(output_dir)
        print("[5/6] 프레임 필터링 완료")

        print("\n[6/6] 프레임 매칭 시작...")
        self.matcher.match_frames(output_dir)
        print("[6/6] 프레임 매칭 완료")
        
        print("\n=== ASD Converter 완료 ===")
        print(f"결과가 {output_dir}에 저장되었습니다.")


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