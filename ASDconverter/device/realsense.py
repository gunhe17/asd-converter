import csv
import time
from pathlib import Path
import pyrealsense2 as rs
import multiprocessing as mp
from dotenv import load_dotenv

load_dotenv()


class Realsense:
    def __init__(self):
        self.rs_convert_exe = 'C:/Users/insighter/workspace/sdk/realsense/tools/rs-convert.exe'
        
        self.csv_dir_name = "realsense/csv"
        self.csv_filename = "frames.csv"
        
        self.color_dir_name = "realsense/color"
        self.color_prefix = "color"
        self.color_file_pattern = "color_Color_{timestamp:.14f}.png"

        self.depth_dir_name = "realsense/depth"
        self.depth_prefix = "depth"
        self.depth_file_pattern = "depth_Depth_{timestamp:.14f}.bin"

    ##
    # Private
        
    def _convert_color(self, args):
        rs_convert_exe, bag_path, color_dir = args
        cmd = [str(rs_convert_exe), "-i", str(bag_path), "-p", str(color_dir / self.color_prefix), "-c"]
        # return subprocess.run(cmd, capture_output=True).returncode == 0
        return True

    def _convert_depth(self, args):
        rs_convert_exe, bag_path, depth_dir = args
        cmd = [str(rs_convert_exe), "-i", str(bag_path), "-p", str(depth_dir / self.depth_prefix), "-d"]
        # return subprocess.run(cmd, capture_output=True).returncode == 0
        return True

    def _generate_csv(self, args):
        bag_path, csv_dir = args
        pipeline = rs.pipeline()    # type: ignore
        config = rs.config()        # type: ignore
        config.enable_device_from_file(str(bag_path), repeat_playback=False)
        
        profile = pipeline.start(config)
        profile.get_device().as_playback().set_real_time(False)

        csv_file = csv_dir / self.csv_filename
        file_exists = csv_file.exists()

        with open(csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'index', 
                'frame_timestamp', 
                'color_frame_index', 
                'color_timestamp', 
                'color_backend_timestamp', 
                'color_hardware_timestamp', 
                'color_arrival_time', 
                'color_file_path', 
                'depth_frame_index', 
                'depth_timestamp', 
                'depth_backend_timestamp', 
                'depth_hardware_timestamp', 
                'depth_arrival_time', 
                'depth_file_path'
            ])
            
            if not file_exists or csv_file.stat().st_size == 0:
                writer.writeheader()

            index = 0
            try:
                while True:
                    frames = pipeline.wait_for_frames()
                    color_frame = frames.get_color_frame()
                    depth_frame = frames.get_depth_frame()

                    if color_frame and depth_frame:
                        writer.writerow({
                            'index': index,
                            'frame_timestamp': f"{frames.get_timestamp():.14f}",
                            'color_frame_index': color_frame.get_frame_number(),
                            'color_timestamp': f"{color_frame.get_timestamp():.14f}",
                            'color_backend_timestamp': color_frame.get_frame_metadata(rs.frame_metadata_value.backend_timestamp),   # type: ignore
                            'color_hardware_timestamp': color_frame.get_frame_metadata(rs.frame_metadata_value.frame_timestamp),    # type: ignore
                            'color_arrival_time': color_frame.get_frame_metadata(rs.frame_metadata_value.time_of_arrival),          # type: ignore
                            'color_file_path': f"color_Color_{color_frame.get_timestamp():.14f}.png",
                            'depth_frame_index': depth_frame.get_frame_number(),
                            'depth_timestamp': f"{depth_frame.get_timestamp():.14f}",
                            'depth_backend_timestamp': depth_frame.get_frame_metadata(rs.frame_metadata_value.backend_timestamp),   # type: ignore
                            'depth_hardware_timestamp': depth_frame.get_frame_metadata(rs.frame_metadata_value.frame_timestamp),    # type: ignore
                            'depth_arrival_time': depth_frame.get_frame_metadata(rs.frame_metadata_value.time_of_arrival),          # type: ignore
                            'depth_file_path': f"depth_Depth_{depth_frame.get_timestamp():.14f}.bin"
                        })
                        index += 1
                        
            except RuntimeError:
                pass
            finally:
                pipeline.stop()
        return True
    
    def _update_csv_indices(self, csv_file: Path):
        if not csv_file.exists():
            return
            
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

    ##
    # Public

    def unit(
        self, 
        bag_file: str, 
        output_dir: str
    ) -> bool:
        bag_path = Path(bag_file)
        output_path = Path(output_dir)
        
        (output_path / self.color_dir_name).mkdir(parents=True, exist_ok=True)
        (output_path / self.depth_dir_name).mkdir(parents=True, exist_ok=True)
        (output_path / self.csv_dir_name).mkdir(parents=True, exist_ok=True)

        # RUN
        
        with mp.Pool(processes=3) as pool:
            color_task = pool.apply_async(
                self._convert_color, 
                ((self.rs_convert_exe, bag_path, output_path / self.color_dir_name),)
            )
            depth_task = pool.apply_async(
                self._convert_depth, 
                ((self.rs_convert_exe, bag_path, output_path / self.depth_dir_name),)
            )
            time.sleep(2)
            csv_task = pool.apply_async(
                self._generate_csv, 
                ((bag_path, output_path / self.csv_dir_name),)
            )
            
            success = all(
                [color_task.get(), depth_task.get(), csv_task.get()]
            )
        
        if success:
            csv_file = output_path / self.csv_dir_name / self.csv_filename
            self._update_csv_indices(csv_file)
        
        return success

    def convert(self, input_dir: str, output_dir: str) -> bool:
        """RealSense session들의 bag 파일을 변환"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # session_*_realsense 폴더들 찾기
        session_dirs = sorted(input_path.glob("session_*_realsense"))
        if not session_dirs:
            return False
        
        success = True
        for session_dir in session_dirs:
            bag_files = list(session_dir.glob("*.bag"))
            if not bag_files:
                continue
                
            bag_file = str(bag_files[0])
            if not self.unit(bag_file, str(output_path)):
                success = False
        
        # 모든 변환 완료 후 CSV 인덱스 업데이트
        if success:
            csv_file = output_path / self.csv_dir_name / self.csv_filename
            self._update_csv_indices(csv_file)
        
        return success