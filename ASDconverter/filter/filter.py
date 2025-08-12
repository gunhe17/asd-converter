import csv
from pathlib import Path


class Filter:
    def __init__(self):
        self.player_csv_path = "player/csv/frames.csv"
        self.realsense_csv_path = "realsense/csv/frames.csv"
        self.tobii_csv_path = "tobii/csv/frames.csv"

    def _extract_valid_ranges(self, player_csv_file):
        """player CSV에서 유효한 재생 범위들 추출"""
        valid_ranges = []
        
        with open(player_csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        print(f"Player CSV total rows: {len(rows)}")
        
        # play-stop 쌍으로 범위 생성
        i = 0
        while i < len(rows):
            if rows[i]['type'] == 'play':
                play_time = float(rows[i]['timestamp'])
                video_id = rows[i]['video_id']
                
                # 다음 행이 stop인지 확인
                if i + 1 < len(rows) and rows[i + 1]['type'] == 'stop':
                    stop_time = float(rows[i + 1]['timestamp'])
                    valid_ranges.append({
                        'video_id': video_id,
                        'start': play_time,
                        'end': stop_time
                    })
                    print(f"Video {video_id}: {play_time:.3f} ~ {stop_time:.3f}")
                    i += 2
                else:
                    print(f"Warning: Play without matching stop for video {video_id}")
                    i += 1
            else:
                i += 1
                
        return valid_ranges

    def _is_timestamp_valid(self, timestamp, valid_ranges):
        """타임스탬프가 유효한 범위 내에 있는지 확인"""
        try:
            timestamp_float = float(timestamp)
            for range_info in valid_ranges:
                if range_info['start'] <= timestamp_float <= range_info['end']:
                    return True, range_info['video_id']
            return False, None
        except (ValueError, TypeError):
            return False, None

    def _filter_csv_file(self, csv_file, valid_ranges, timestamp_column='frame_timestamp'):
        """CSV 파일에서 유효한 타임스탬프를 가진 행만 필터링"""
        if not csv_file.exists():
            print(f"File not found: {csv_file}")
            return 0
        
        print(f"Filtering {csv_file.name}...")
        
        filtered_rows = []
        total_rows = 0
        video_counts = {}
        
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            if timestamp_column not in fieldnames: # type: ignore
                print(f"Warning: {timestamp_column} column not found in {csv_file.name}")
                return 0
            
            for row in reader:
                total_rows += 1
                is_valid, video_id = self._is_timestamp_valid(row[timestamp_column], valid_ranges)
                
                if is_valid:
                    filtered_rows.append(row)
                    video_counts[video_id] = video_counts.get(video_id, 0) + 1
        
        print(f"  Total rows: {total_rows}")
        print(f"  Valid rows: {len(filtered_rows)}")
        print(f"  Frames per video: {video_counts}")
        
        # 필터링된 결과를 새 파일로 저장 (index 재정렬)
        if filtered_rows:
            for i, row in enumerate(filtered_rows):
                row['index'] = i
            
            # 파일명에 _filtered 추가
            filtered_file = csv_file.parent / f"{csv_file.stem}_filtered{csv_file.suffix}"
            
            with open(filtered_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames) # type: ignore
                writer.writeheader()
                writer.writerows(filtered_rows)
            
            print(f"  Saved to: {filtered_file.name}")
        
        return len(filtered_rows)

    def filter_frames(self, output_dir):
        """모든 프레임 데이터를 player 기준으로 필터링"""
        output_path = Path(output_dir)
        
        # player CSV에서 유효한 범위 추출
        player_csv = output_path / self.player_csv_path
        if not player_csv.exists():
            print(f"Player CSV file not found: {player_csv}")
            return False
        
        print("=" * 50)
        print("EXTRACTING VALID RANGES FROM PLAYER DATA")
        print("=" * 50)
        
        valid_ranges = self._extract_valid_ranges(player_csv)
        print(f"\nTotal valid ranges: {len(valid_ranges)}")
        
        if not valid_ranges:
            print("No valid ranges found!")
            return False
        
        print("\n" + "=" * 50)
        print("FILTERING REALSENSE DATA")
        print("=" * 50)
        
        # realsense CSV 필터링
        realsense_csv = output_path / self.realsense_csv_path
        realsense_count = self._filter_csv_file(realsense_csv, valid_ranges, 'frame_timestamp')
        
        print("\n" + "=" * 50)
        print("FILTERING TOBII DATA") 
        print("=" * 50)
        
        # tobii CSV 필터링
        tobii_csv = output_path / self.tobii_csv_path
        tobii_count = self._filter_csv_file(tobii_csv, valid_ranges, 'frame_timestamp')
        
        print("\n" + "=" * 50)
        print("FILTERING COMPLETE")
        print("=" * 50)
        print(f"Realsense frames after filtering: {realsense_count}")
        print(f"Tobii frames after filtering: {tobii_count}")
        
        return True