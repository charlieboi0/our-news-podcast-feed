import argparse
import podcast_episode_processor as processor
import add_new_episode
import time

if __name__ == "__main__":
    start_time = time.perf_counter()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-de', '--disable-execute-check',
        help='Disable the check for whether the action is within a certain time frame',
        action="store_true"
    )
    args = parser.parse_args()
    
    processor.process_latest_podcast(args.disable_execute_check)
    add_new_episode.add_to_feed()

    end_time = time.perf_counter()
    print(f'\nTime to complete: {(end_time - start_time) // 60:.0f}m {(end_time - start_time) % 60:.3f}s')
    
