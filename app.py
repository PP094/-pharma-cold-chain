"""Streamlit dashboard for pharmaceutical cold-chain monitoring."""

from pathlib import Path

import pandas as pd
import streamlit as st

from cold_chain import classify_readings, load_readings, summarize_readings

st.set_page_config(
    page_title="药品冷链监控系统",
    page_icon="🌡️",
    layout="wide",
)

DEFAULT_DATA = Path(__file__).parent / "data" / "sample_temperature.csv"


@st.cache_data
def read_default_data() -> pd.DataFrame:
    return load_readings(DEFAULT_DATA)


def render_sidebar() -> tuple[pd.DataFrame, float, float]:
    st.sidebar.header("数据与规则")
    uploaded_file = st.sidebar.file_uploader("上传温度 CSV", type=["csv"])
    lower_limit = st.sidebar.number_input("温度下限（°C）", value=2.0, step=0.5)
    upper_limit = st.sidebar.number_input("温度上限（°C）", value=8.0, step=0.5)

    if uploaded_file is None:
        readings = read_default_data()
        st.sidebar.caption("当前使用内置示例数据")
    else:
        try:
            readings = load_readings(uploaded_file)
            st.sidebar.success(f"已读取 {len(readings)} 条记录")
        except ValueError as exc:
            st.sidebar.error(str(exc))
            readings = read_default_data()

    return readings, lower_limit, upper_limit


def render_kpis(summary: dict[str, int | float]) -> None:
    columns = st.columns(5)
    columns[0].metric("监测记录", f"{summary['total']:,}")
    columns[1].metric("设备数量", f"{summary['devices']:,}")
    columns[2].metric("告警数量", f"{summary['alarms']:,}")
    columns[3].metric("告警率", f"{summary['alarm_rate']}%")
    columns[4].metric("平均温度", f"{summary['average']} °C")


def main() -> None:
    st.title("🌡️ 药品冷链监控系统")
    st.caption("实时掌握运输与仓储温度，及时识别药品冷链风险")

    readings, lower_limit, upper_limit = render_sidebar()
    if lower_limit >= upper_limit:
        st.error("温度下限必须小于上限，请调整侧边栏规则。")
        return

    classified = classify_readings(readings, lower_limit, upper_limit)
    summary = summarize_readings(classified)
    render_kpis(summary)

    st.subheader("温度趋势")
    trend = classified.set_index("timestamp")[["temperature"]]
    st.line_chart(trend, y="temperature", use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("设备状态")
        device_status = (
            classified.assign(is_alarm=classified["status"] != "正常")
            .groupby("device_id", as_index=False)
            .agg(
                location=("location", "first"),
                latest_temperature=("temperature", "last"),
                alarm_count=("is_alarm", "sum"),
            )
        )
        device_status["状态"] = device_status["alarm_count"].map(
            lambda count: "告警" if count else "正常"
        )
        st.dataframe(
            device_status.rename(
                columns={
                    "device_id": "设备编号",
                    "location": "位置",
                    "latest_temperature": "最新温度（°C）",
                    "alarm_count": "告警次数",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    with right:
        st.subheader("告警分布")
        status_counts = classified["status"].value_counts().rename_axis("状态").to_frame("记录数")
        st.bar_chart(status_counts, y="记录数", use_container_width=True)

    st.subheader("告警记录")
    alarms = classified[classified["status"] != "正常"].copy()
    if alarms.empty:
        st.success("当前没有超出温度范围的记录。")
    else:
        st.warning(f"发现 {len(alarms)} 条温度告警，请及时核查。")
        st.dataframe(
            alarms[
                ["timestamp", "device_id", "location", "temperature", "status", "deviation"]
            ].rename(
                columns={
                    "timestamp": "时间",
                    "device_id": "设备编号",
                    "location": "位置",
                    "temperature": "温度（°C）",
                    "status": "告警类型",
                    "deviation": "偏差（°C）",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
