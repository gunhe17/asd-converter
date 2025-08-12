import csv
from pathlib import Path


class Matcher:
    def __init__(self):
        self.realsense_filtered_path = "realsense/csv/frames_filtered.csv"
        self.tobii_filtered_path = "tobii/csv/frames_filtered.csv"
        self.matched_output_path = "matched/csv/frames_matched.csv"
        self.max_time_diff = 100.0

    def _load_csv_data(self, csv_file):
        """CSV 파일을 로드하고 타임스탬프 기준으로 정렬"""
        data = []
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['frame_timestamp'] = float(row['frame_timestamp'])
                data.append(row)
        
        data.sort(key=lambda x: x['frame_timestamp'])
        return data

    def _find_closest_match(self, target_timestamp, tobii_data, used_indices, start_index=0):
        """target_timestamp에 가장 가까운 사용되지 않은 tobii 프레임 찾기"""
        best_match = None
        best_diff = float('inf')
        best_index = None
        
        # 이진 탐색으로 시작 위치 최적화
        left, right = start_index, len(tobii_data) - 1
        search_start = start_index
        
        while left <= right:
            mid = (left + right) // 2
            if tobii_data[mid]['frame_timestamp'] < target_timestamp:
                search_start = mid
                left = mid + 1
            else:
                right = mid - 1
        
        # 최적 매칭 찾기
        search_range = 100
        start_search = max(0, search_start - search_range)
        end_search = min(len(tobii_data), search_start + search_range)
        
        for i in range(start_search, end_search):
            if i in used_indices:
                continue
                
            candidate = tobii_data[i]
            time_diff = abs(candidate['frame_timestamp'] - target_timestamp)
            
            if time_diff < best_diff and time_diff <= self.max_time_diff:
                best_diff = time_diff
                best_match = candidate
                best_index = i
        
        return best_match, best_index, best_diff

    def _determine_video_id(self, timestamp, valid_ranges):
        """타임스탬프가 속한 video_id 찾기"""
        for range_info in valid_ranges:
            if range_info['start'] <= timestamp <= range_info['end']:
                return range_info['video_id']
        return None

    def _create_matched_row(self, realsense_row, tobii_row, time_diff, video_id):
        """매칭된 두 프레임을 하나의 row로 합치기"""
        matched_row = {
            'index': 0,
            'tobii_timestamp': tobii_row['frame_timestamp'] if tobii_row else None,
            'frame_hardware_timestamp': tobii_row['frame_hardware_timestamp'] if tobii_row else None,
            'left_gaze_display_x': tobii_row['left_gaze_display_x'] if tobii_row else None,
            'left_gaze_display_y': tobii_row['left_gaze_display_y'] if tobii_row else None,
            'left_gaze_3d_x': tobii_row['left_gaze_3d_x'] if tobii_row else None,
            'left_gaze_3d_y': tobii_row['left_gaze_3d_y'] if tobii_row else None,
            'left_gaze_3d_z': tobii_row['left_gaze_3d_z'] if tobii_row else None,
            'left_gaze_validity': tobii_row['left_gaze_validity'] if tobii_row else None,
            'left_gaze_origin_x': tobii_row['left_gaze_origin_x'] if tobii_row else None,
            'left_gaze_origin_y': tobii_row['left_gaze_origin_y'] if tobii_row else None,
            'left_gaze_origin_z': tobii_row['left_gaze_origin_z'] if tobii_row else None,
            'left_gaze_origin_validity': tobii_row['left_gaze_origin_validity'] if tobii_row else None,
            'left_pupil_diameter': tobii_row['left_pupil_diameter'] if tobii_row else None,
            'left_pupil_validity': tobii_row['left_pupil_validity'] if tobii_row else None,
            'right_gaze_display_x': tobii_row['right_gaze_display_x'] if tobii_row else None,
            'right_gaze_display_y': tobii_row['right_gaze_display_y'] if tobii_row else None,
            'right_gaze_3d_x': tobii_row['right_gaze_3d_x'] if tobii_row else None,
            'right_gaze_3d_y': tobii_row['right_gaze_3d_y'] if tobii_row else None,
            'right_gaze_3d_z': tobii_row['right_gaze_3d_z'] if tobii_row else None,
            'right_gaze_validity': tobii_row['right_gaze_validity'] if tobii_row else None,
            'right_gaze_origin_x': tobii_row['right_gaze_origin_x'] if tobii_row else None,
            'right_gaze_origin_y': tobii_row['right_gaze_origin_y'] if tobii_row else None,
            'right_gaze_origin_z': tobii_row['right_gaze_origin_z'] if tobii_row else None,
            'right_gaze_origin_validity': tobii_row['right_gaze_origin_validity'] if tobii_row else None,
            'right_pupil_diameter': tobii_row['right_pupil_diameter'] if tobii_row else None,
            'right_pupil_validity': tobii_row['right_pupil_validity'] if tobii_row else None,
            'realsense_timestamp': realsense_row['frame_timestamp'],
            'rgb_path': realsense_row['color_file_path'],
            'depth_path': realsense_row['depth_file_path'],
            'video_id': video_id,
            'time_diff_ms': f"{time_diff:.3f}" if time_diff != float('inf') else 'NO_MATCH',
        }
        
        return matched_row

    def _extract_valid_ranges(self, player_csv_file):
        """player CSV에서 유효한 재생 범위들 추출"""
        valid_ranges = []
        
        with open(player_csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        i = 0
        while i < len(rows):
            if rows[i]['type'] == 'play':
                play_time = float(rows[i]['timestamp'])
                video_id = rows[i]['video_id']
                
                if i + 1 < len(rows) and rows[i + 1]['type'] == 'stop':
                    stop_time = float(rows[i + 1]['timestamp'])
                    valid_ranges.append({
                        'video_id': video_id,
                        'start': play_time,
                        'end': stop_time
                    })
                    i += 2
                else:
                    i += 1
            else:
                i += 1
                
        return valid_ranges

    def match_frames(self, output_dir):
        """필터링된 realsense와 tobii 프레임을 타임스탬프 기준으로 매칭"""
        output_path = Path(output_dir)
        
        # 입력 파일 확인
        realsense_file = output_path / self.realsense_filtered_path
        tobii_file = output_path / self.tobii_filtered_path
        player_file = output_path / "player/csv/frames.csv"
        
        for file in [realsense_file, tobii_file, player_file]:
            if not file.exists():
                print(f"Required file not found: {file}")
                return False
        
        print("=" * 60)
        print("LOADING DATA")
        print("=" * 60)
        
        # 유효 범위 및 데이터 로드
        valid_ranges = self._extract_valid_ranges(player_file)
        realsense_data = self._load_csv_data(realsense_file)
        tobii_data = self._load_csv_data(tobii_file)
        
        print(f"Realsense frames: {len(realsense_data):,}")
        print(f"Tobii frames: {len(tobii_data):,}")
        print(f"Valid video ranges: {len(valid_ranges)}")
        
        print("\n" + "=" * 60)
        print("MATCHING FRAMES")
        print("=" * 60)
        
        # 매칭 수행
        matched_rows = []
        used_tobii_indices = set()
        match_count = 0
        total_time_diff = 0
        last_search_index = 0
        
        for i, rs_row in enumerate(realsense_data):
            if i % 1000 == 0:
                print(f"Processing: {i:,}/{len(realsense_data):,} ({i/len(realsense_data)*100:.1f}%)")
            
            rs_timestamp = rs_row['frame_timestamp']
            video_id = self._determine_video_id(rs_timestamp, valid_ranges)
            
            # 가장 가까운 tobii 프레임 찾기
            tb_match, tb_index, time_diff = self._find_closest_match(
                rs_timestamp, tobii_data, used_tobii_indices, last_search_index
            )
            
            if tb_match:
                # 매칭 성공
                matched_row = self._create_matched_row(rs_row, tb_match, time_diff, video_id)
                matched_rows.append(matched_row)
                used_tobii_indices.add(tb_index)
                match_count += 1
                total_time_diff += time_diff
                last_search_index = max(0, tb_index - 10) # type: ignore
            else:
                # 매칭 실패
                matched_row = self._create_matched_row(rs_row, None, float('inf'), video_id)
                matched_rows.append(matched_row)
        
        # 결과 통계
        print(f"\nMatching complete!")
        print(f"Successfully matched: {match_count:,}")
        print(f"Unmatched realsense frames: {len(realsense_data) - match_count:,}")
        print(f"Unmatched tobii frames: {len(tobii_data) - len(used_tobii_indices):,}")
        print(f"Match rate: {match_count/len(realsense_data)*100:.2f}%")
        
        if match_count > 0:
            avg_time_diff = total_time_diff / match_count
            print(f"Average time difference: {avg_time_diff:.3f}ms")
        
        # 결과 저장
        if matched_rows:
            output_csv_path = output_path / self.matched_output_path
            output_csv_path.parent.mkdir(parents=True, exist_ok=True)
            
            # index 재정렬
            for i, row in enumerate(matched_rows):
                row['index'] = i
            
            fieldnames = list(matched_rows[0].keys())
            
            with open(output_csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(matched_rows)
            
            print(f"\nMatched data saved to: {output_csv_path}")
            print(f"Total rows: {len(matched_rows):,}")
            print(f"Columns: {len(fieldnames)}")
        
        return True