import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import base64


class ScanHistory:
    def __init__(self, conn):
        self.conn = conn

    def scans_in_range(self, retailer, start=None, end=None):
        retailer_clean = retailer.strip().lower()

        query = """
        SELECT scan_date as day, COUNT(*) as count
        from scan_events
        WHERE LOWER(retailer) = ?
        """
        params = [retailer_clean]

        if start:
            if isinstance(start, pd.Timestamp):
                start = start.strftime("%Y-%m-%d")
            query += " AND scan_date >= ?"
            params.append(start)

        if end:
            if isinstance(end, pd.Timestamp):
                end = end.strftime("%Y-%m-%d")
            query += " AND scan_date <= ?"
            params.append(end)

        query += " GROUP BY day ORDER BY day"
        df = pd.read_sql_query(query, self.conn, params=params)
        print("DEBUG SCANS QUERY:", query)
        print("DEBUG PARAMS:", params)
        print("DEBUG SCANS DF:", df)
        return df
    
    def scans_last_n_months(self, retailer, n):
        start = (pd.Timestamp.today().replace(day=1) - pd.DateOffset(months=n))
        return self.scans_in_range(retailer, start)
    
    def scans_n_months_ago(self, retailer, n):
        start = (pd.Timestamp.today().replace(day=1) - pd.DateOffset(month=n))
        end = start + pd.DateOffset(month=1)
        df = self.scans_in_range(retailer, start, end)
        return int(df["count"].sum())
    
    def scans_full_history(self, retailer):
        return self.scans_in_range(retailer)
    
    def scans_this_year(self, retailer):
        start = pd.Timestamp.today().replace(month=1, day=1)
        return self.scans_in_range(retailer, start)
    
    def scans_monthly_history(self, retailer):
        df = self.scans_full_history(retailer)

        if df.empty:
            return None
        
        df["day"] = pd.to_datetime(df["day"])

        monthly = (
            df.set_index("day").resample("MS").sum().reset_index()
        )

        return monthly
    
    def format_monthly_counts(self, df):
        return "\n".join(f"{row['day'].strftime('%b %Y')}: {int(row['count'])}" for _, row in df.iterrows()) 
    
    def plot_scan_history(self, df, retailer, title="Scan History"):
        if df.empty:
            return None
        
        df['day'] = pd.to_datetime(df['day'])
        df_monthly = (df.set_index('day').resample('M').sum().reset_index())

        plt.figure(figsize=(8, 4.5))
        plt.plot(df_monthly['day'], df_monthly['count'], linewidth=2.5, marker='o', markersize=6, linestyle='-', color='green')
        plt.title(f"{title} for {retailer}", fontsize=14, fontweight="bold", pad=12)
        plt.xlabel("Month", fontsize=11, labelpad=8)
        plt.ylabel("Number of Scans", fontsize=11, labelpad=8)
        plt.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.5)
        ax = plt.gca()
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        months = df_monthly['day'].dt.strftime("%b")
        plt.xticks(df_monthly['day'], months, rotation=45, ha="right")

        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=200)
        plt.close()
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return f"data:image/png;base64,{img_base64}"


