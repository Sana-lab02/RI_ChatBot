import matplotlib
matplotlib.use("Agg")
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from prophet import Prophet
import matplotlib.pyplot as plt
from io import BytesIO
import base64

class ScanPredictor:
    def __init__(self, conn):
        self.conn = conn

    def retailer_exists(self, retailer):
        query = "SELECT 1 FROM retailers WHERE LOWER(retailer) = ? LIMIT 1"
        df = pd.read_sql_query(query, self.conn, params=(retailer.lower(),))
        return not df.empty


    def get_historical_scans(self, retailer):
        query = """
        SELECT retailer, scan_date
        FROM scan_events
        WHERE LOWER(retailer) = ?
        """
        df = pd.read_sql_query(query, self.conn, params=(retailer.lower(),))
        if df.empty:
            return pd.DataFrame()

        df["scan_date"] = pd.to_datetime(df["scan_date"])
        df["ds"] = df["scan_date"].dt.to_period("M").dt.to_timestamp()

        monthly = df.groupby("ds").size().reset_index(name="scan_count")

       
        all_months = pd.date_range(
            monthly["ds"].min(),
            pd.Timestamp.today().replace(day=1),
            freq="MS"
        )

        monthly = monthly.set_index("ds").reindex(all_months, fill_value=0).reset_index()
        monthly.rename(columns={"index": "ds"}, inplace=True)

        return monthly


    
    def predict_scans(self, retailer, months=12):
        forecast_months = pd.date_range(
            pd.Timestamp.today().replace(day=1),
            periods=12,
            freq="MS"
        )

        data = self.get_historical_scans(retailer)
        print(data)
        n_months = len(data)
        if n_months == 0:
            return pd.DataFrame({
                "ds": forecast_months,
                "predicted_scan_count": [0]*len(forecast_months)
            })

       
        rolling_avg = data["scan_count"].rolling(window=min(3, n_months), min_periods=1).mean().iloc[-1]

        # Activity factor
        real_data = data[data["scan_count"] > 0]
        latest_date = real_data["ds"].max()
        months_since_last_scan = (pd.Timestamp.today() - latest_date).days / 30.44

        scans_last_6m = real_data.loc[
            real_data["ds"] >= latest_date - pd.DateOffset(month=6), "scan_count"
        ].sum()

        avg_scans_per_month = real_data["scan_count"].mean()

        if avg_scans_per_month >= 2 or scans_last_6m >= 4:
            activity_factor = 1.0
        elif scans_last_6m >= 2:
            activity_factor = 0.8
        elif months_since_last_scan <= 3:
            activity_factor = 0.5
        elif months_since_last_scan <= 6:
            activity_factor = 0.3
        else:
            activity_factor = 0.3

        
        predictions = None

        if n_months >= 12:
            try:
                prophet_data = data.rename(columns={"scan_count":"y"})[["ds","y"]]
                m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
                m.fit(prophet_data)

                future = pd.DataFrame({"ds": forecast_months})
                forecast = m.predict(future)
                forecast["yhat"] = (0.7 * forecast["yhat"] + 0.3 * rolling_avg)
                forecast["yhat"] = np.clip(forecast["yhat"], 0, max(2*rolling_avg, 1))
                forecast["yhat"] *= activity_factor
                forecast["yhat"] = forecast["yhat"].round()

                predictions = forecast[["ds","yhat"]].rename(columns={"yhat":"predicted_scan_count"})

            except Exception as e:
               
                predictions = pd.DataFrame({
                    "ds": forecast_months,
                    "predicted_scan_count": np.round(rolling_avg * activity_factor)
                })
        else:
           
            predictions = pd.DataFrame({
                "ds": forecast_months,
                "predicted_scan_count": np.round(rolling_avg * activity_factor)
            })

        predictions["retailer"] = retailer
        return predictions

    def generate_graph(self, retailer, predictions):
        plt.figure(figsize=(8,4.5))
        plt.plot(predictions["ds"], predictions["predicted_scan_count"], linewidth=2.5, marker='o', markersize=6, linestyle='-', color='green')
        plt.title(f"Predicted Scans for {retailer}", fontsize=14, fontweight="bold", pad=12)
        plt.xlabel("Month", fontsize=11, labelpad=8)
        plt.ylabel("Scan Count", fontsize=11, labelpad=8)
        months = predictions["ds"].dt.strftime("%b")
        plt.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.5)
        ax = plt.gca()
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.xticks(predictions["ds"], months, rotation=45, ha="right")
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"
    
    def predict_scans_with_graph(self, retailer, months=12):
        predictions = self.predict_scans(retailer, months)

        predictions = predictions.head(months)

        image = self.generate_graph(retailer, predictions)

        return {
            "predictions": predictions,
            "image": image
        }
