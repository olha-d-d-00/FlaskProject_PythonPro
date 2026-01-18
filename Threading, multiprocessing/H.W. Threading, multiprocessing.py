import datetime
import logging
import threading
import time
from multiprocessing import Process


def happy_ticket(start_number, end_number, thread_num):
    count = 0
    for i in range(start_number, end_number):
        if find_happy_nums(i):
            count += 1
            # print(i, end=', ') #раскоментировать чтобы получить подробную информацию о lucky числах

    print(f"{thread_num}: {count}")


def find_happy_nums(num: int) -> bool:
    digits = str(num).zfill(6)
    first_half = digits[:3]
    last_half = digits[3:]
    return sum(map(int, first_half)) == sum(map(int, last_half))


if __name__ == '__main__':
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")


    START_NUMBER_TICKET = 0
    END_NUMBER_TICKET = 1000000
    MIDDLE_NUM = (START_NUMBER_TICKET + END_NUMBER_TICKET) // 2

    logging.info("Main      : before creating thread")
    # Раскомментировать при переведении на Threading
    # x1 = threading.Thread(target=happy_ticket, args=(100000, 100500, "thread 1"))
    # x2 = threading.Thread(target=happy_ticket, args=(200000, 200500, "thread 2"))
    x1 = Process(target=happy_ticket, args=(START_NUMBER_TICKET, MIDDLE_NUM, "thread 1"))
    x2 = Process(target=happy_ticket, args=(MIDDLE_NUM, END_NUMBER_TICKET, "thread 2"))
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