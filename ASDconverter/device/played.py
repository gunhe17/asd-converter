import csv
from pathlib import Path
from datetime import datetime
import pytz


class Played:
    def __init__(self):
        self.csv_dir_name = "."
        self.csv_filename = "played.csv"

    def _convert_timestamp(self, iso_timestamp):
        """ISO 8601 UTC 형식을 한국 시간 기준 밀리초 타임스탬프로 변환"""
        dt_utc = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        kst = pytz.timezone('Asia/Seoul')
        dt_kst = dt_utc.astimezone(kst)
        return dt_kst.timestamp() * 1000

    def _create_play_stop_pairs(self, rows):
        """모든 play event를 순차적으로 처리하여 play-end/pause 쌍 생성"""
        
        # 1단계: 메타데이터 수집
        # 각 video_id별 모든 play의 index 수집
        video_play_indices = {}
        for i, row in enumerate(rows):
            if row['type'] == 'play':
                video_id = row['video_id']
                if video_id not in video_play_indices:
                    video_play_indices[video_id] = []
                video_play_indices[video_id].append(i)
        
        # 각 video_id별 마지막 play의 index 식별
        video_last_play_index = {}
        for video_id, indices in video_play_indices.items():
            video_last_play_index[video_id] = indices[-1] if indices else -1
        
        # 전체 마지막 video_id 식별
        all_video_ids = set(row['video_id'] for row in rows if row['type'] == 'play')
        last_video_id = max(all_video_ids, key=int) if all_video_ids else None
        
        # 2단계: 순차 처리
        play_stop_pairs = []
        skip_indices = set()  # 이미 처리된 end/pause의 index
        
        for i, row in enumerate(rows):
            # skip 목록에 있으면 건너뛰기
            if i in skip_indices:
                continue
                
            if row['type'] == 'play':
                video_id = row['video_id']
                start_time = self._convert_timestamp(row['time'])
                
                # 이 play가 해당 video의 마지막 play인지 확인
                is_last_play = (i == video_last_play_index[video_id])
                
                # 3단계: Pair 찾기
                stop_time_str = None
                stop_type = None
                stop_index = None
                
                for j in range(i + 1, len(rows)):
                    next_event = rows[j]
                    
                    # 같은 video_id의 end event
                    if next_event['type'] == 'end' and next_event['video_id'] == video_id:
                        stop_time = self._convert_timestamp(next_event['time'])
                        stop_time_str = f"{stop_time:.14f}"
                        stop_type = 'end'
                        stop_index = j
                        break
                        
                    # 같은 video_id의 pause event
                    elif next_event['type'] == 'pause' and next_event['video_id'] == video_id:
                        pause_time = self._convert_timestamp(next_event['time'])
                        stop_time_str = f"{pause_time:.14f}"
                        stop_type = 'pause'
                        stop_index = j
                        break
                
                # pair가 없는 경우 기본값 처리
                if stop_time_str is None:
                    stop_time = start_time + 30000
                    stop_time_str = f"{stop_time:.14f}"
                    stop_type = 'end'
                
                # valid 값 결정
                if is_last_play and stop_type == 'end':
                    valid = True
                elif is_last_play and video_id == last_video_id and stop_type == 'pause':
                    # 마지막 video의 마지막 play-pause는 end로 변경하고 valid=True
                    stop_type = 'end'
                    valid = True
                else:
                    valid = False
                
                # 결과에 추가
                play_stop_pairs.extend([
                    {
                        'index': 0,
                        'timestamp': f"{start_time:.14f}",
                        'video_id': video_id,
                        'type': 'play',
                        'valid': valid
                    },
                    {
                        'index': 0,
                        'timestamp': stop_time_str,
                        'video_id': video_id,
                        'type': stop_type,
                        'valid': valid
                    }
                ])
                
                # 처리한 stop event를 skip 목록에 추가
                if stop_index is not None:
                    skip_indices.add(stop_index)
        
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
            fieldnames = ['index', 'timestamp', 'video_id', 'type', 'valid']
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
        """Played CSV 변환"""
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