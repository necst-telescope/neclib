import concurrent.futures
import time

import pytest

from neclib.utils import busy


class TestBusy:
    def test_function_executed_normally(self):
        class A:
            def task(self):
                with busy(self, "busy"):
                    return 1

        assert A().task() == 1

    def test_concurrent_execution(self):
        class A:
            def task(self):
                with busy(self, "busy"):
                    time.sleep(0.3)
                    return time.time()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            a = A()
            future1 = executor.submit(a.task)
            future2 = executor.submit(a.task)
            concurrent.futures.wait([future1, future2])
            assert abs(future1.result() - future2.result()) < 0.5

    def test_multiple_task_groups(self):
        class A:
            def task_a(self):
                with busy(self, "busy_a"):
                    time.sleep(0.3)
                    return time.time()

            def task_b(self):
                with busy(self, "busy_b"):
                    time.sleep(0.3)
                    return time.time()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            a = A()
            future1 = executor.submit(a.task_a)
            future2 = executor.submit(a.task_b)
            future3 = executor.submit(a.task_a)
            future4 = executor.submit(a.task_b)
            concurrent.futures.wait([future1, future2, future3, future4])
            assert abs(future1.result() - future3.result()) < 0.5
            assert abs(future2.result() - future4.result()) < 0.5

    def test_raise_error_if_flagname_already_exists_as_classvar(self):
        class A:
            busy = 1

            def task(self):
                with busy(self, "busy"):
                    return 1

        a = A()
        with pytest.raises(ValueError):
            a.task()

    def test_raise_error_if_flagname_already_exists_as_instance_var(self):
        class A:
            def __init__(self):
                self.busy = 1

            def task(self):
                with busy(self, "busy"):
                    return 1

        a = A()
        with pytest.raises(ValueError):
            a.task()

    def test_raise_error_on_execution_failure(self):
        class A:
            def task(self):
                with busy(self, "busy"):
                    raise ValueError

        a = A()
        with pytest.raises(ValueError):
            a.task()

    def test_cleanly_exits_even_if_error(self):
        class A:
            def task(self, a):
                with busy(self, "busy"):
                    return a / 2

        a = A()
        with pytest.raises(TypeError):
            a.task("a")
        assert a.task(2) == 1
