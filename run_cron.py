# run_cron.py - chạy tất cả các job update NDVI, LST, TVDI

from app.services.ndvi_update_3d import update_ndvi
from app.services.lst_weekly_update import update_lst_weekly_to_mongo
from app.services.tvdi_weekly_update import update_tvdi_weekly
from datetime import datetime

def main():
    print("=== NDVI ===")
    try:
        update_ndvi()
    except Exception as e:
        print("NDVI update error:", e)

    print("\n=== LST ===")
    try:
        update_lst_weekly_to_mongo()
    except Exception as e:
        print("LST update error:", e)

    print("\n=== TVDI ===")
    try:
        update_tvdi_weekly()
    except Exception as e:
        print("TVDI update error:", e)

    print("\n DONE ALL UPDATES ")


    with open("D:/WebGis/task_log.txt", "a", encoding="utf-8") as f:
        f.write(f"Task ran at {datetime.now()}\n")


if __name__ == "__main__":
    main()
