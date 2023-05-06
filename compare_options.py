# Author: Austin Benny

from datetime import datetime
from textwrap import dedent
import numpy as np

from wallstreet import Call, Put


class CompareContracts:
    def __init__(self, contract):
        (
            self.ticker,
            self.strike,
            self.expiry,
            self.contract_type,
        ) = self.extract_specs(contract).values()
        self.contr_name = contract

        option = self._get_contract(
            self.ticker, self.strike, self.expiry, self.contract_type
        )
        metrics = self._calculate_metrics(option)
        self._write_metrics(metrics, option)

    def _write_metrics(self, metrics, option):
        # TODO: Use jinja
        # TODO: Better output

        perc_delta_money = (self.strike - option["underlying_price"]) / option[
            "underlying_price"
        ]
        baseline_name, baseline_option, baseline_metrics = self._get_baseline_option(
            perc_delta_money
        )

        out_str = dedent(
            f"""
            ____________________________________
            {self.contr_name} [Run on: {datetime.now().strftime("%a %d %b %Y, %I:%M%p")}]
            __________________
            {metrics['sample_perc_change']:.0%} move in ${self.ticker}          = {metrics['contr_perc_change']:.2%} move in option
            1 day move in ${self.ticker}       = {metrics['theta_change']:.2%} decrease in option
            {metrics['sample_perc_change']:.0%} IV move in ${self.ticker}       = {metrics['iv_change']:.2%} move in option
            delta/premium            = {metrics['delta_prem']:.2f}
            gamma/delta              = {metrics['gamma_del']:.2f}
            extrinsicValue/theta     = {metrics['ext_theta']:.2f}
            ask-bid spread           = {metrics['ask_bid_spread']:.2%}
            premium                  = ${option['premium']}
            __________________
            Baseline: {baseline_name}
            __________________
            {baseline_metrics['sample_perc_change']:.0%} move in ${self.ticker}          = {baseline_metrics['contr_perc_change']:.2%} move in option
            1 day move in ${self.ticker}       = {baseline_metrics['theta_change']:.2%} decrease in option
            {baseline_metrics['sample_perc_change']:.0%} IV move in ${self.ticker}       = {baseline_metrics['iv_change']:.2%} move in option
            delta/premium            = {baseline_metrics['delta_prem']:.2f}
            gamma/delta              = {baseline_metrics['gamma_del']:.2f}
            extrinsicValue/theta     = {baseline_metrics['ext_theta']:.2f}
            ask-bid spread           = {baseline_metrics['ask_bid_spread']:.2%}
            premium                  = ${baseline_option['premium']}
            ____________________________________
            """
        )

        print(out_str)

    def _calculate_metrics(self, option):
        metrics = {}

        metrics["ask_bid_spread"] = option["ask"] - option["bid"]
        metrics["ask_bid_perc_diff"] = float(
            metrics["ask_bid_spread"] / ((option["ask"] + option["bid"]) / 2)
        )

        if self.strike < option["underlying_price"]:
            metrics["extrensic_value"] = option["premium"] - (
                option["underlying_price"] - self.strike
            )
        else:
            metrics["extrensic_value"] = option["premium"]

        metrics["sample_perc_change"] = 0.01
        metrics["delta_change"] = (
            option["delta"] * option["underlying_price"] * metrics["sample_perc_change"]
        )
        metrics["contr_perc_change"] = metrics["delta_change"] / option["premium"]
        metrics["iv_change"] = option["vega"] / option["premium"]
        metrics["non_dim_iv"] = metrics["iv_change"] / option["iv"]
        metrics["theta_change"] = option["theta"] / option["premium"]
        metrics["break_even"] = (metrics["theta_change"] * option["premium"]) / (
            option["underlying_price"] * option["delta"]
        )
        metrics["delta_prem"] = option["delta"] / option["premium"]
        metrics["gamma_del"] = option["gamma"] / option["delta"]
        metrics["ext_theta"] = metrics["extrensic_value"] / option["theta"]
        # # indexes
        # metrics["g_d_index"] = self.ratio_in_index(option["gamma"], option["delta"])
        # metrics["d_p_index"] = self.ratio_in_index(option["delta"], option["premium"])
        # metrics["e_t_index"] = self.ratio_in_index(option["extrensic_value"], option["theta"])
        # metrics["non_dim_iv_index"] = self.ratio_in_index(metrics["iv_change"], option["iv"])

        return metrics

    @staticmethod
    def _get_contract(ticker, strike, expiry, contract_type):
        if contract_type == "P":
            ws_contr = Put(
                ticker,
                strike=strike,
                d=expiry["day"],
                m=expiry["month"],
                y=expiry["year"],
            )
        else:
            ws_contr = Call(
                ticker,
                strike=strike,
                d=expiry["day"],
                m=expiry["month"],
                y=expiry["year"],
            )

        option = {}

        option["premium"] = float(ws_contr.price)
        option["underlying_price"] = float(ws_contr.underlying.price)
        option["delta"] = float(ws_contr.delta())
        option["theta"] = float(ws_contr.theta())
        option["gamma"] = float(ws_contr.gamma())
        option["vega"] = float(ws_contr.vega())
        option["iv"] = float(ws_contr.implied_volatility())
        option["bid"] = float(ws_contr.bid)
        option["ask"] = float(ws_contr.ask)

        return option

    def _get_baseline_option(self, perc_delta_money):
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = (np.abs(array - value)).argmin()

            return array[idx]

        if self.contract_type == "P":
            ws_contr = Put(
                "SPY",
                d=self.expiry["day"],
                m=self.expiry["month"],
                y=self.expiry["year"],
            )
        else:
            ws_contr = Call(
                "SPY",
                d=self.expiry["day"],
                m=self.expiry["month"],
                y=self.expiry["year"],
            )

        prop_strike_baseline = (1 + perc_delta_money) * ws_contr.underlying.price
        spy_strike = find_nearest(list(ws_contr.strikes), prop_strike_baseline)
        spy_contr_name = (
            f"SPY "
            f"{self.expiry['month']}-{self.expiry['day']}-{self.expiry['year']} "
            f"{spy_strike}{self.contract_type}"
        )

        option = self._get_contract("SPY", spy_strike, self.expiry, self.contract_type)
        metrics = self._calculate_metrics(option)

        return spy_contr_name, option, metrics

    @staticmethod
    def ratio_in_index(var1, var2):
        """converts the ratios into an index between 0 and 100 kinda like the RSI"""
        return 100 - (100 / (1 + (var1 / var2)))

    @staticmethod
    def extract_specs(spec_str: str) -> dict[str]:
        spec_list = spec_str.split(" ")
        ticker = spec_list[0]
        expiry = spec_list[1]
        strike = spec_list[-1][:-1]
        contract_type = spec_str[-1]

        # Error check
        if not ticker.isalpha():
            raise TypeError(
                f"Incorrectly specified ticker [{ticker}] in input string [{spec_str}]."
            )
        if not strike.isnumeric():
            raise TypeError(
                f"Incorrectly specified strike [{strike}] in input string [{spec_str}]."
            )
        if not contract_type.isalpha():
            raise TypeError(
                (
                    "Incorrectly specified contract type "
                    f"[{contract_type}] in input string [{spec_str}]."
                )
            )
        try:
            datetime.strptime(expiry, "%M-%d-%Y")
        except ValueError:
            raise ValueError(
                f"Incorrect data format for date {expiry}, should be MM-DD-YYYY."
            )

        month, day, year = expiry.split("-")

        return {
            "ticker": ticker.upper(),
            "strike": float(strike),
            "expiry": {"month": int(month), "day": int(day), "year": int(year)},
            "contract_type": contract_type.upper(),
        }

    @staticmethod
    def convert_to_contract_symbol(inp_dict: dict[str]) -> str:
        return (
            f"{inp_dict['ticker']}"
            + f"{inp_dict['year']}{inp_dict['month']}{inp_dict['day']}"
            + f"{inp_dict['contract_type']}"
            + f"{1000 * float(inp_dict['strike']):08}"
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="compare_options",
        description="Quick script to provide information on derivatives.",
    )

    parser.add_argument(
        "contract",
        help=(
            "Provide the contract specs in standard syntax. For example, "
            "a Call option for SPY at strike price $400 for expiration 06/16/2022 "
            "should be input as `'SPY 06-16-2023 400C'`. Note the quotation marks."
        ),
    )
    args = parser.parse_args()

    CompareContracts(args.contract)
