# Author: Austin Benny

from datetime import datetime
from textwrap import dedent

from wallstreet import Call, Put


class CompareContracts:
    def __init__(self, contract):
        self.inp_contr = self.extract_specs(contract)
        (
            self.ticker,
            self.expiry,
            self.strike,
            self.contract_type,
        ) = self.inp_contr.values()

        option = self._get_contract()
        metrics = self._calculate_metrics(option)
        self._write_metrics(metrics)

    def _write_metrics(self, metrics):
        # TODO: Use jinja
        out_str = dedent(
            f"""
            __________________
            {self.convert_to_informal_ref(self.inp_contr)} [Run on: {datetime.now()}]
            __________________
            {metrics['sample_perc_change']:.0%} move in ${self.ticker}          = {metrics['contr_perc_change']:.2%} move in option
            1 day move in ${self.ticker}       = {metrics['theta_change']:.2%} decrease in option
            {metrics['sample_perc_change']:.0%} IV move in ${self.ticker}       = {metrics['iv_change']:.2%} move in option
            delta/premium            = {metrics['delta_prem']:.2f}
            gamma/delta              = {metrics['gamma_del']:.2f}
            extrinsicValue/theta     = {metrics['ext_theta']:.2f}
            ask-bid spread           = {metrics['ask_bid_perc_diff']:.2%}
            __________________
            """
        )

        print(out_str)

    def _calculate_metrics(self, option):
        metrics = {}

        metrics["ask_bid_perc_diff"] = float(
            (option["ask"] - option["bid"]) / ((option["ask"] + option["bid"]) / 2)
        )

        if self.strike < option["underlying_price"]:
            metrics["extrensicVal"] = (
                option["premium"] - (option["underlying_price"] - self.strike)
            )
        else:
            metrics["extrensicVal"] = option["premium"]

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
        metrics["ext_theta"] = option["extrensicVal"] / option["theta"]
        # # indexes
        # metrics["g_d_index"] = self.ratio_in_index(option["gamma"], option["delta"])
        # metrics["d_p_index"] = self.ratio_in_index(option["delta"], option["premium"])
        # metrics["e_t_index"] = self.ratio_in_index(option["extrensicVal"], option["theta"])
        # metrics["non_dim_iv_index"] = self.ratio_in_index(metrics["iv_change"], option["iv"])

        return metrics

    def _get_contract(self):
        if self.contract_type == "P":
            #TODO: change constructor
            ws_contr = Put(ticker=self.ticker, expiration=self.expiry, strike=self.strike)
        else:
            ws_contr = Call(ticker=self.ticker, expiration=self.expiry, strike=self.strike)

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
                f"Incorrectly specified contract type [{contract_type}] in input string [{spec_str}]."
            )
        try:
            datetime.strptime(expiry, "%M-%d-%Y")
        except ValueError:
            raise ValueError(
                f"Incorrect data format for date {expiry}, should be MM-DD-YYYY."
            )

        return {
            "ticker": ticker.upper(),
            "strike": strike,
            "expiry": str(expiry),
            "contract_type": contract_type.upper(),
        }

    @staticmethod
    def convert_to_contract_symbol(inp_dict: dict[str]) -> str:
        expiry = datetime.strptime(inp_dict["expiry"], "%M-%d-%Y").strftime("%y%M%d")

        return (
            f"{inp_dict['ticker']}"
            + f"{expiry}"
            + f"{inp_dict['contract_type']}"
            + f"{1000 * float(inp_dict['strike']):08}"
        )

    @staticmethod
    def convert_to_informal_ref(inp_dict: dict[str]) -> str:
        return f"{inp_dict['ticker']} {inp_dict['expiry']} {inp_dict['strike']}{inp_dict['contract_type']}"


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
            "should be input as `SPY 06-16-2023 400C`"
        ),
    )
    args = parser.parse_args()

    CompareContracts(args.contract)
