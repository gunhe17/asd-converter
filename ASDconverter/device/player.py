import csv
from pathlib import Path
from datetime import datetime
import pytz


class Player:
    def __init__(self):
        self.csv_dir_name = "player/csv"
        self.csv_filename = "frames.csv"

    def _convert_timestamp(self, iso_timestamp):
        """ISO 8601 UTC 형식을 한국 시간 기준 밀리초 타임스탬프로 변환"""
        dt_utc = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        kst = pytz.timezone('Asia/Seoul')
        dt_kst = dt_utc.astimezone(kst)
        return dt_kst.timestamp() * 1000

    def _create_play_stop_pairs(self, rows):
        """각 video_id의 마지막 play만 추출하여 play-stop 쌍 생성"""
        # 각 video_id별 마지막 play 찾기
        video_last_play = {}
        for row in rows:
            if row['type'] == 'play':
                video_last_play[row['video_id']] = row
        
        # 원본 로그에서 각 마지막 play의 위치 찾기
        play_positions = {}
        for i, row in enumerate(rows):
            video_id = row['video_id']
            if (row['type'] == 'play' and 
                video_id in video_last_play and
                row['time'] == video_last_play[video_id]['time']):
                play_positions[video_id] = i
        
        play_stop_pairs = []

        for video_id in sorted(video_last_play.keys(), key=int):
            play_event = video_last_play[video_id]
            play_pos = play_positions[video_id]
            start_time = self._convert_timestamp(play_event['time'])
            
            stop_time_str = None
            for j in range(play_pos + 1, len(rows)):
                next_event = rows[j]
                if next_event['type'] == 'play':
                    next_time = self._convert_timestamp(next_event['time'])
                    stop_time_str = f"{next_time:.14f}".replace('00000000000000', '99999999999999')
                    if stop_time_str.endswith('.99999999999999'):
                        integer_part = int(stop_time_str.split('.')[0]) - 1
                        stop_time_str = f"{integer_part}.99999999999999"
                    break

                elif (next_event['type'] == 'pause' and next_event['video_id'] == video_id):
                    pause_time = self._convert_timestamp(next_event['time'])
                    stop_time_str = f"{pause_time:.14f}".replace('00000000000000', '99999999999999')
                    if stop_time_str.endswith('.99999999999999'):
                        integer_part = int(stop_time_str.split('.')[0]) - 1
                        stop_time_str = f"{integer_part}.99999999999999"
                    break
            
            if stop_time_str is None:
                stop_time = start_time + 30000
                stop_time_str = f"{stop_time:.14f}"
            
            play_stop_pairs.extend([
                {
                    'index': 0,
                    'timestamp': f"{start_time:.14f}",
                    'video_id': play_event['video_id'],
                    'type': 'play'
                },
                {
                    'index': 0,
                    'timestamp': stop_time_str,  # 문자열 직접 사용
                    'video_id': play_event['video_id'],
                    'type': 'stop'
                }
            ])

        return play_stop_pairs

    def _convert_play_csv(self, input_csv_path, output_csv_path):
        # 원본 데이터 읽기
        with open(input_csv_path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)
        
        # play-stop 쌍 생성
        converted_rows = self._create_play_stop_pairs(all_rows)
        
        # CSV 파일 생성
        if converted_rows:
            fieldnames = ['index', 'timestamp', 'video_id', 'type']
            with open(output_csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(converted_rows)
                
        return len(converted_rows) > 0

    def _update_csv_indices(self, csv_file):
        """CSV 인덱스 업데이트"""
        rows = []
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
        
        for i, row in enumerate(rows):
            row['index'] = i
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames) # type: ignore
            writer.writeheader()
            writer.writerows(rows)

    def convert(self, input_dir, output_dir):
        """Player CSV 변환"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        (output_path / self.csv_dir_name).mkdir(parents=True, exist_ok=True)
        
        play_csv = input_path / "play.csv"
        if not play_csv.exists():
            return False
        
        output_csv_path = output_path / self.csv_dir_name / self.csv_filename
        success = self._convert_play_csv(play_csv, output_csv_path)
        
        if success:
            self._update_csv_indices(output_csv_path)
        
        return success