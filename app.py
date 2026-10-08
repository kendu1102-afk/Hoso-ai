import streamlit as st
import pandas as pd
from io import BytesIO
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ----------------- GIAO DIỆN STREAMLIT -----------------
st.set_page_config(page_title="Trợ lý Hồ sơ Dự toán & Hoàn công", layout="wide")
st.title("🏗️ Trợ lý Tự động Xử lý Hồ sơ Dự toán & Hoàn công")
st.caption("Tải file thô (Excel, CSV, văn bản) -> AI bóc tách -> Xuất bảng Excel hoàn chỉnh")

# Cấu hình API Key
api_key = st.sidebar.text_input("Nhập Gemini API Key:", type="password")

# ----------------- ĐỊNH NGHĨA DỮ LIỆU ĐẦU RA -----------------
class CongTacItem(BaseModel):
    stt: int = Field(description="Số thứ tự công tác")
    ma_hieu: str = Field(description="Mã hiệu định mức dự toán đề xuất hoặc theo tài liệu")
    ten_cong_tac: str = Field(description="Tên chi tiết công việc/hạng mục")
    don_vi: str = Field(description="Đơn vị tính (m3, tấn, m2, cái,...)")
    khoi_luong: float = Field(description="Khối lượng tương ứng")
    ghi_chu: str = Field(description="Ghi chú về kiểm tra logic hoặc lưu ý hồ sơ")

class DanhSachCongTac(BaseModel):
    danh_sach: list[CongTacItem]

# ----------------- XỬ LÝ TẢI FILE VÀ GỌI AI -----------------
uploaded_file = st.file_uploader("Tải lên file dữ liệu thô (Excel, CSV, TXT):", type=["xlsx", "xls", "csv", "txt"])

if uploaded_file and api_key:
    # Đọc dữ liệu đầu vào
    noi_dung = ""
    try:
        if uploaded_file.name.endswith(".csv"):
            df_in = pd.read_csv(uploaded_file)
            noi_dung = df_in.to_string()
        elif uploaded_file.name.endswith((".xlsx", ".xls")):
            df_in = pd.read_excel(uploaded_file)
            noi_dung = df_in.to_string()
        else:
            noi_dung = uploaded_file.read().decode("utf-8")
        st.info("Đã nạp file thành công. Nhấn nút bên dưới để AI tự động xử lý.")
    except Exception as e:
        st.error(f"Lỗi khi đọc file: {e}")

    if st.button("🚀 Bắt đầu Tự động Xử lý"):
        with st.spinner("AI đang bóc tách, chuẩn hóa mã hiệu và lập bảng khối lượng..."):
            try:
                client = genai.Client(api_key=api_key)

                prompt_he_thong = (
                    "Bạn là Kỹ sư Kinh tế Xây dựng chuyên trách lập hồ sơ dự toán, "
                    "thanh quyết toán và hoàn công. Hãy đọc kỹ dữ liệu thô được cung cấp, "
                    "lọc bỏ các thông tin rác, gán mã hiệu định mức phù hợp theo định mức xây dựng hiện hành, "
                    "tổng hợp khối lượng rõ ràng và ghi chú những điểm cần lưu ý kiểm tra."
                )

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[prompt_he_thong, f"Dữ liệu thô:\n{noi_dung}"],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=DanhSachCongTac,
                    ),
                )

                # Chuyển đổi kết quả JSON thành bảng Excel
                data_json = response.text
                danh_sach = DanhSachCongTac.model_validate_json(data_json)
                
                rows = []
                for item in danh_sach.danh_sach:
                    rows.append({
                        "STT": item.stt,
                        "Mã hiệu định mức": item.ma_hieu,
                        "Tên công tác / Hạng mục": item.ten_cong_tac,
                        "Đơn vị tính": item.don_vi,
                        "Khối lượng": item.khoi_luong,
                        "Ghi chú kiểm tra": item.ghi_chu
                    })
                
                df_out = pd.DataFrame(rows)
                st.success("✅ Đã xử lý xong! Kiểm tra bảng xem trước bên dưới:")
                st.dataframe(df_out, use_container_width=True)

                # Nút tải file Excel về máy
                output_buffer = BytesIO()
                with pd.ExcelWriter(output_buffer, engine="openpyxl") as writer:
                    df_out.to_excel(writer, index=False, sheet_name="Bang_Khoi_Luong")
                
                st.download_button(
                    label="📥 Tải file Excel hoàn chỉnh về máy",
                    data=output_buffer.getvalue(),
                    file_name="Ho_So_Chuan_Hoa.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"Có lỗi xảy ra trong quá trình xử lý: {e}")

elif not api_key:
    st.warning("Vui lòng nhập Gemini API Key ở thanh bên trái để sử dụng.")
