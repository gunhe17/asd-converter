import csv
from pathlib import Path
import numpy as np


class Matcher:
    def __init__(self):
        self.realsense_filtered_path = "realsense/csv/filtered.csv"
        self.tobii_filtered_path = "tobii/csv/filtered.csv"
        
        self.matched_output_path = "frames.csv"

        self.max_time_diff = 100.0

    def _load_csv_data(self, csv_file):
        """CSV 파일을 로드하고 타임스탬프 기준으로 정렬"""
        data = []
        with open(csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get('frame_timestamp', '').strip()
                if ts == '':
                    # timestamp가 비어있으면 건너뜀
                    continue
                try:
                    row['frame_timestamp'] = float(ts)
                except ValueError:
                    # 변환 불가능한 값도 건너뜀
                    continue
                data.append(row)
        
        data.sort(key=lambda x: x['frame_timestamp'])
        return data

    def _hungarian_algorithm(self, cost_matrix):
        """Hungarian Algorithm으로 최적 할당 찾기"""
        # scipy 없이 간단한 구현
        n_rows, n_cols = cost_matrix.shape
        assignments = []
        
        # 작은 크기의 경우 brute force
        if n_rows <= 10 and n_cols <= 10:
            from itertools import permutations
            
            if n_rows <= n_cols:
                min_cost = float('inf')
                best_assignment = None
                
                for perm in permutations(range(n_cols), n_rows):
                    cost = sum(cost_matrix[i, perm[i]] for i in range(n_rows))
                    if cost < min_cost:
                        min_cost = cost
                        best_assignment = list(perm)
                
                assignments = [(i, best_assignment[i]) for i in range(n_rows)] # type: ignore
            else:
                # n_rows > n_cols인 경우
                min_cost = float('inf')
                best_assignment = None
                
                for perm in permutations(range(n_rows), n_cols):
                    cost = sum(cost_matrix[perm[j], j] for j in range(n_cols))
                    if cost < min_cost:
                        min_cost = cost
                        best_assignment = list(perm)
                
                assignments = [(best_assignment[j], j) for j in range(n_cols)] # type: ignore
        else:
            # 큰 크기의 경우 greedy approximation
            used_cols = set()
            for i in range(n_rows):
                best_j = None
                best_cost = float('inf')
                
                for j in range(n_cols):
                    if j not in used_cols and cost_matrix[i, j] < best_cost:
                        best_cost = cost_matrix[i, j]
                        best_j = j
                
                if best_j is not None and best_cost < float('inf'):
                    assignments.append((i, best_j))
                    used_cols.add(best_j)
        
        return assignments

    def _match_frames(self, realsense_data, tobii_data, valid_ranges):
        """2-pass 매칭: 먼저 최적 매칭을 찾고, 충돌을 해결"""
        
        # 1st Pass: 각 RS frame에 대해 최적 TB frame 찾기 (중복 허용)
        preliminary_matches = []
        
        for rs_idx, rs_row in enumerate(realsense_data):
            rs_timestamp = rs_row['frame_timestamp']
            
            # 이진 탐색으로 중심점 찾기
            left, right = 0, len(tobii_data) - 1
            center_idx = 0
            
            while left <= right:
                mid = (left + right) // 2
                if tobii_data[mid]['frame_timestamp'] < rs_timestamp:
                    center_idx = mid
                    left = mid + 1
                else:
                    right = mid - 1
            
            # 앞뒤 5개 프레임에서 최적 찾기
            best_tb_idx = None
            best_diff = float('inf')
            
            search_range = 5
            start_idx = max(0, center_idx - search_range)
            end_idx = min(len(tobii_data), center_idx + search_range + 1)
            
            for tb_idx in range(start_idx, end_idx):
                time_diff = abs(tobii_data[tb_idx]['frame_timestamp'] - rs_timestamp)
                
                if time_diff < best_diff and time_diff <= self.max_time_diff:
                    best_diff = time_diff
                    best_tb_idx = tb_idx
            
            preliminary_matches.append({
                'rs_idx': rs_idx,
                'tb_idx': best_tb_idx,
                'time_diff': best_diff
            })
        
        # 2nd Pass: 충돌 해결 - 동일한 TB를 원하는 RS들 중 가장 가까운 것 선택
        tb_to_rs = {}  # TB index -> (RS index, time_diff)
        
        for match in preliminary_matches:
            if match['tb_idx'] is None:
                continue
                
            tb_idx = match['tb_idx']
            rs_idx = match['rs_idx']
            time_diff = match['time_diff']
            
            if tb_idx not in tb_to_rs or time_diff < tb_to_rs[tb_idx][1]:
                # 이 TB에 대해 첫 매칭이거나, 더 가까운 RS를 찾은 경우
                tb_to_rs[tb_idx] = (rs_idx, time_diff)
        
        # 최종 매칭 결과 생성
        matched_rows = []
        match_count = 0
        total_time_diff = 0
        
        # RS index -> TB index 역매핑
        rs_to_tb = {}
        for tb_idx, (rs_idx, time_diff) in tb_to_rs.items():
            rs_to_tb[rs_idx] = (tb_idx, time_diff)
        
        # 결과 생성
        for rs_idx, rs_row in enumerate(realsense_data):
            video_id = self._determine_video_id(rs_row['frame_timestamp'], valid_ranges)
            
            if rs_idx in rs_to_tb:
                tb_idx, time_diff = rs_to_tb[rs_idx]
                tb_row = tobii_data[tb_idx]
                matched_row = self._create_matched_row(rs_row, tb_row, time_diff, video_id)
                match_count += 1
                total_time_diff += time_diff
            else:
                matched_row = self._create_matched_row(rs_row, None, float('inf'), video_id)
            
            matched_rows.append(matched_row)
        
        unmatched_rs_count = len(realsense_data) - match_count
        unmatched_tb_count = len(tobii_data) - len(tb_to_rs)
        
        return matched_rows, match_count, unmatched_rs_count, unmatched_tb_count, total_time_diff

    def match_frames_simple(self, realsense_csv: str, tobii_csv: str, output_csv: str | None = None, max_time_diff: float | None = None) -> bool:
        """
        played.csv의 valid range를 완전히 배제하고, 두 CSV 간 matching만 수행.
        - realsense_csv: Realsense filtered CSV path
        - tobii_csv: Tobii filtered CSV path
        - output_csv: 출력 파일 경로(.csv). 미지정 시 현재 작업 디렉토리의 self.matched_output_path 사용
        - max_time_diff: ms 단위 제한값(옵션). 지정 시 self.max_time_diff를 덮어씀
        """
        from pathlib import Path

        if max_time_diff is not None:
            self.max_time_diff = float(max_time_diff)

        realsense_file = Path(realsense_csv)
        tobii_file = Path(tobii_csv)

        for file in [realsense_file, tobii_file]:
            if not file.exists():
                print(f"Required file not found: {file}")
                return False

        print("=" * 60)
        print("LOADING DATA (NO VALID RANGES)")
        print("=" * 60)

        # valid_ranges 비움 -> video_id는 항상 None
        valid_ranges: list[dict] = []

        realsense_data = self._load_csv_data(realsense_file)
        tobii_data = self._load_csv_data(tobii_file)

        print(f"Realsense frames: {len(realsense_data):,}")
        print(f"Tobii frames: {len(tobii_data):,}")

        print("\n" + "=" * 60)
        print("GLOBAL OPTIMAL MATCHING (RANGE DISABLED)")
        print("=" * 60)

        matched_rows, match_count, unmatched_rs_count, unmatched_tb_count, total_time_diff = \
            self._match_frames(realsense_data, tobii_data, valid_ranges)

        print(f"\nMatching complete!")
        print(f"Successfully matched: {match_count:,}")
        print(f"Unmatched realsense frames: {unmatched_rs_count:,}")
        print(f"Unmatched tobii frames: {unmatched_tb_count:,}")
        print(f"Match rate: {match_count/len(realsense_data)*100:.2f}%")

        if match_count > 0:
            avg_time_diff = total_time_diff / match_count
            print(f"Average time difference: {avg_time_diff:.3f}ms")
            time_diffs = [float(row['time_diff_ms']) for row in matched_rows if row['time_diff_ms'] != 'NO_MATCH']
            if time_diffs:
                print(f"Min time difference: {min(time_diffs):.3f}ms")
                print(f"Max time difference: {max(time_diffs):.3f}ms")

        # 출력 경로 결정
        if output_csv is None:
            output_path = Path(self.matched_output_path)
        else:
            out_p = Path(output_csv)
            if out_p.is_dir():
                output_path = out_p / self.matched_output_path
            else:
                output_path = out_p

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # index 재정렬 후 저장
        for i, row in enumerate(matched_rows):
            row['index'] = i
            row['video_id'] = None  # range 미사용이므로 명시적으로 None

        if matched_rows:
            fieldnames = list(matched_rows[0].keys())
            with open(output_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(matched_rows)

            print(f"\nMatched data saved to: {output_path}")
            print(f"Total rows: {len(matched_rows):,}")
            print(f"Columns: {len(fieldnames)}")

        return True

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
            'tobii_timestamp': f"{float(tobii_row['frame_timestamp']):.14f}" if tobii_row else None,
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
            'realsense_timestamp': f"{float(realsense_row['frame_timestamp']):.14f}",
            'rgb_path': realsense_row['color_file_path'],
            'depth_path': realsense_row['depth_file_path'],
            'video_id': video_id,
            'time_diff_ms': f"{time_diff:.3f}" if time_diff != float('inf') else 'NO_MATCH',
        }
        
        return matched_row

    def _extract_valid_ranges(self, played_csv_file):
        """played CSV에서 유효한 재생 범위들 추출"""
        valid_ranges = []
        
        with open(played_csv_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        i = 0
        while i < len(rows):
            if rows[i]['type'] == 'play' and rows[i].get('valid', 'True') == 'True':
                play_time = float(rows[i]['timestamp'])
                video_id = rows[i]['video_id']
                
                if i + 1 < len(rows) and rows[i + 1]['type'] in ['end', 'pause']:
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
        """필터링된 realsense와 tobii 프레임을 전역 최적 매칭"""
        output_path = Path(output_dir)
        
        # 입력 파일 확인
        realsense_file = output_path / self.realsense_filtered_path
        tobii_file = output_path / self.tobii_filtered_path
        played_file = output_path / "played.csv"
        
        for file in [realsense_file, tobii_file, played_file]:
            if not file.exists():
                print(f"Required file not found: {file}")
                return False
        
        print("=" * 60)
        print("LOADING DATA")
        print("=" * 60)
        
        # 유효 범위 및 데이터 로드
        valid_ranges = self._extract_valid_ranges(played_file)
        realsense_data = self._load_csv_data(realsense_file)
        tobii_data = self._load_csv_data(tobii_file)
        
        print(f"Realsense frames: {len(realsense_data):,}")
        print(f"Tobii frames: {len(tobii_data):,}")
        print(f"Valid video ranges: {len(valid_ranges)}")
        
        print("\n" + "=" * 60)
        print("GLOBAL OPTIMAL MATCHING")
        print("=" * 60)
        
        # 전역 최적 매칭 수행
        matched_rows, match_count, unmatched_rs_count,unmatched_tb_count, total_time_diff = self._match_frames(realsense_data, tobii_data, valid_ranges)
        
        # 결과 통계
        print(f"\nMatching complete!")
        print(f"Successfully matched: {match_count:,}")
        print(f"Unmatched realsense frames: {unmatched_rs_count:,}")
        print(f"Unmatched tobii frames: {unmatched_tb_count:,}")
        print(f"Match rate: {match_count/len(realsense_data)*100:.2f}%")
        
        if match_count > 0:
            avg_time_diff = total_time_diff / match_count
            print(f"Average time difference: {avg_time_diff:.3f}ms")
            
            # 시간차 분포 분석
            time_diffs = [float(row['time_diff_ms']) for row in matched_rows if row['time_diff_ms'] != 'NO_MATCH']
            if time_diffs:
                print(f"Min time difference: {min(time_diffs):.3f}ms")
                print(f"Max time difference: {max(time_diffs):.3f}ms")
        
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
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Realsense–Tobii frame matching (valid ranges disabled).")
    parser.add_argument("--realsense", required=True, help="Realsense filtered CSV path")
    parser.add_argument("--tobii", required=True, help="Tobii filtered CSV path")
    parser.add_argument("--out", default=None, help="Output CSV file path (or directory). Default: frames.csv")
    parser.add_argument("--max-diff", type=float, default=None, help="Max time diff in ms (override).")

    args = parser.parse_args()

    matcher = Matcher()
    matcher.match_frames_simple(
        realsense_csv=args.realsense,
        tobii_csv=args.tobii,
        output_csv=args.out,
        max_time_diff=args.__dict__.get("max_diff")
    )
