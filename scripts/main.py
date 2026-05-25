import podcast_episode_processor as processor
import add_new_episode
import time

if __name__ == "__main__":
    start_time = time.perf_counter()

    processor.process_latest_podcast()
    add_new_episode.add_to_feed()

    end_time = time.perf_counter()
    print(f'\nTime to complete: {(end_time - start_time) // 60:.0f}m {(end_time - start_time) % 60:.3f}s')
    