import shutil
from pathlib import Path


class User:
    def __init__(self):
        self.txt_dir_name = "."
        self.txt_filename = "user.txt"
        self.input_txt_filename = "user.txt"

    def convert(self, input_dir, output_dir):
        """user.txt 파일 복사"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        print("User 텍스트 파일 처리 중...")
        # 출력 디렉토리 생성
        (output_path / self.txt_dir_name).mkdir(parents=True, exist_ok=True)
        
        # 입력 파일 확인
        input_txt = input_path / self.input_txt_filename
        if not input_txt.exists():
            print(f"User 파일을 찾을 수 없습니다: {input_txt}")
            return False
        
        print(f"파일 복사 중: {input_txt.name}")
        # 출력 파일 경로
        output_txt_path = output_path / self.txt_dir_name / self.txt_filename
        
        try:
            # 파일 복사
            shutil.copy2(input_txt, output_txt_path)
            print(f"파일 복사 완료: {input_txt} -> {output_txt_path}")
            return True
            
        except Exception as e:
            print(f"파일 복사 실패: {e}")
            return False