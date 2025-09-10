import csv
from pathlib import Path


class Tobii:
    def __init__(self):
        self.csv_dir_name = "tobii/csv"
        self.csv_filename = "frames.csv"

    def _merge_csv_files(self, session_dirs, output_csv_path):
        all_rows = []
        fieldnames = None
        
        for session_dir in session_dirs:
            csv_files = list(session_dir.glob("*.csv"))
            if not csv_files:
                continue
                
            with open(csv_files[0], 'r', newline='') as f:
                reader = csv.DictReader(f)
                if fieldnames is None:
                    fieldnames = [field for field in reader.fieldnames if field is not None] # type: ignore
                
                for row in reader:
                    clean_row = {k: v for k, v in row.items() if k is not None}
                    all_rows.append(clean_row)
        
        # write merged csv
        if all_rows and fieldnames:
            with open(output_csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_rows)
                
        return len(all_rows) > 0
    
    def _update_csv_indices(self, csv_file):
        rows = []
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        # index 업데이트
        for i, row in enumerate(rows):
            row['index'] = i
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames) # type: ignore
            writer.writeheader()
            writer.writerows(rows)

    def convert(self, input_dir, output_dir):
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        print("Tobii 세션 폴더 검색 중...")
        (output_path / self.csv_dir_name).mkdir(parents=True, exist_ok=True)
        
        session_dirs = sorted(input_path.glob("session_*_tobii"))
        if not session_dirs:
            print("Tobii 세션 폴더를 찾을 수 없습니다.")
            return False
        
        print(f"발견된 세션 폴더: {len(session_dirs)}개")
        print("Tobii CSV 파일 병합 중...")
        
        output_csv_path = output_path / self.csv_dir_name / self.csv_filename
        success = self._merge_csv_files(session_dirs, output_csv_path)
        
        if success:
            print("CSV 인덱스 업데이트 중...")
            self._update_csv_indices(output_csv_path)
            print("CSV 인덱스 업데이트 완료")
        else:
            print("CSV 병합 실패")
        
        return success