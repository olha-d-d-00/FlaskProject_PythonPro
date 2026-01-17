import datetime
import logging
import threading
import time
from multiprocessing import Process

def calc_prime_number(start_range, end_range, thread_num):
    prime_nums = []
    for i in range(start_range, end_range):
        is_prime = True
        for j in range(2, i):
            if i % j == 0:
                is_prime = False
                break
        if is_prime:
            # print(f"{i} is prime number, thread: {thread_num}")
            prime_nums.append(i)

    print(f"{thread_num} : {prime_nums}")

if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    logging.info("Main      : before creating thread")
    # Раскомментировать при переведении на Threading
    # x1 = threading.Thread(target=calc_prime_number, args=(2, 50000, "thread 1"))
    # x2 = threading.Thread(target=calc_prime_number, args=(50001, 100000, "thread 2"))
    x1 = Process(target=calc_prime_number, args=(2, 50000, "thread 1"))
    x2 = Process(target=calc_prime_number, args=(50001, 100000, "thread 2"))
    logging.info("Main      : before running thread")
    t1 = datetime.datetime.now()
    x1.start()
    x2 .start()
    logging.info("Main      : wait for the thread 1 to finish")
    x1.join()
    logging.info("Main      : wait for the thread 2 to finish")
    x2.join()
    t2  = datetime.datetime.now()
    logging.info("Main      : all done")
    logging.info(f"Time taken: {t2 - t1 }")