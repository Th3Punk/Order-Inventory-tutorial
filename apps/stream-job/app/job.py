from __future__ import annotations

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common import Types


def main() -> None:
    env = StreamExecutionEnvironment.get_execution_environment()

    # minimális adatforrás és operator
    env.from_collection(["ping"], type_info=Types.STRING()).map(lambda x: x)

    env.execute("stream-job")


if __name__ == "__main__":
    main()
