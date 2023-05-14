# Author: Austin Benny

import os
from datetime import datetime
from typing import Type

import numpy as np
from jinja2 import Environment, FileSystemLoader
from wallstreet import Call, Put


class Option:
    def __init__(
        self,
        ticker: str,
        expiry: dict[int],
        strike: float | int | str,
        contract_type: str,
    ):
        self.ticker = ticker.upper()
        self.expiry = {k: int(v) for k, v in expiry.items()}
        self.strike = float(strike)
        self.contract_type = contract_type.upper()
        self.contr_name = self.__str__()

        self._add_option_parameters()

    @classmethod
    def from_ws_obj(cls, ws_obj: Type[Call] | Type[Put]):
        expiry = {}
        ws_expiration = ws_obj.expiration.split("-")
        expiry["month"] = ws_expiration[1]
        expiry["day"] = ws_expiration[0]
        expiry["year"] = ws_expiration[-1]

        return cls(ws_obj.ticker, expiry, ws_obj.strike, ws_obj.Option_type[0])

    def _add_option_parameters(self):
        if self.contract_type == "P":
            ws_contr = Put(
                self.ticker,
                d=self.expiry["day"],
                m=self.expiry["month"],
                y=self.expiry["year"],
                strike=self.strike,
            )
        else:
            ws_contr = Call(
                self.ticker,
                d=self.expiry["day"],
                m=self.expiry["month"],
                y=self.expiry["year"],
                strike=self.strike,
            )

        # Set new attributes
        self.premium = float(ws_contr.price)
        self.underlying_price = float(ws_contr.underlying.price)
        self.delta = float(ws_contr.delta())
        self.theta = float(ws_contr.theta())
        self.gamma = float(ws_contr.gamma())
        self.vega = float(ws_contr.vega())
        self.iv = float(ws_contr.implied_volatility())
        self.bid = float(ws_contr.bid)
        self.ask = float(ws_contr.ask)

    @staticmethod
    def get_contract_symbol(
        ticker, expiry: dict[int], strike: float | int, contract_type: str
    ) -> str:
        return (
            f"{ticker}"
            + f"{expiry['year']}{expiry['month']}{expiry['day']}"
            + f"{contract_type}"
            + f"{1000 * float(strike):08}"
        )

    def __str__(self) -> str:
        return (
            f"{self.ticker} "
            f"{self.expiry['month']}-{self.expiry['day']}-{self.expiry['year']} "
            f"{self.strike}{self.contract_type}"
        )


class Metrics:
    def __init__(self, option: Type[Option]):
        self.ran_on = datetime.now().strftime("%a %d %b %Y, %I:%M%p")
        self._calculate_metrics(option)

    @classmethod
    def from_ws_obj(cls, ws_obj: Type[Call] | Type[Put]):
        option = Option.from_ws_obj(ws_obj)

        return cls(option)

    def _calculate_metrics(self, option: Type[Option]):
        self.ask_bid_spread = option.ask - option.bid
        # Find extrensic value
        if option.strike < option.underlying_price:
            self.extrensic_value = option.premium - (
                option.underlying_price - option.strike
            )
        else:
            self.extrensic_value = option.premium
        # Find option percent change given underlying percent change
        self.sample_perc_change = 0.01

        self.premium_change = (
            option.delta * option.underlying_price * self.sample_perc_change
        )
        self.premium_perc_change = self.premium_change / option.premium
        self.iv_change = option.vega / option.premium
        self.non_dim_iv = self.iv_change / option.iv
        self.theta_change = option.theta / option.premium
        # TODO: check breakeven calc
        self.break_even = (
            self.theta_change
            * option.premium
            * (1 / option.underlying_price * option.delta)
        )
        self.delta_prem = option.delta / option.premium
        self.gamma_del = option.gamma / option.delta
        self.ext_theta = self.extrensic_value / option.theta


class Process:
    def __init__(self, contr_name: str, baseline: bool, scaling: float):
        # Extract conntract identifiers from input contract string
        ticker, expiry, strike, contract_type = self.extract_contract(contr_name)

        # Error check
        if not ticker.isalpha():
            raise TypeError(
                f"Incorrectly specified ticker [{ticker}] in input string [{contr_name}]."
            )
        if not strike.isnumeric():
            raise TypeError(
                f"Incorrectly specified strike [{strike}] in input string [{contr_name}]."
            )
        if not contract_type.isalpha():
            raise TypeError(
                (
                    "Incorrectly specified contr_name type "
                    f"[{contract_type}] in input string [{contr_name}]."
                )
            )

        self.option = Option(ticker, expiry, strike, contract_type)
        self.metrics = Metrics(self.option)

        self._write_metrics(
            self.option.__dict__ | self.metrics.__dict__, baseline, scaling
        )

    def _write_metrics(
        self, merged_dict: dict[float, int, str], baseline: bool, scaling: float
    ):
        templates_path = os.path.dirname(os.path.abspath(__file__))
        environment = Environment(
            loader=FileSystemLoader(os.path.join(templates_path, "templates"))
        )
        template = environment.get_template("metrics_output.j2")

        out_str = template.render(merged_dict)
        print(out_str)

        if baseline:

            perc_delta_money = (
                merged_dict["strike"] - merged_dict["underlying_price"]
            ) * (1 / merged_dict["underlying_price"])
            baseline_option, baseline_metrics = self._get_baseline_option(
                self.option.expiry, self.option.contract_type, perc_delta_money, scaling
            )
            baseline_merged_dict = baseline_option.__dict__ | baseline_metrics.__dict__
            baseline_merged_dict["baseline"] = "Baseline:"
            baseline_template = template.render(baseline_merged_dict)
            print(baseline_template)

    @staticmethod
    def _get_baseline_option(
        expiry: dict[int], contract_type: str, perc_delta_money: float, scaling: float
    ) -> tuple[Type[Option], Type[Metrics]]:
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = (np.abs(array - value)).argmin()

            return array[idx]

        if contract_type == "C":
            spy = Call(
                "SPY",
                d=expiry["day"],
                m=expiry["month"],
                y=expiry["year"],
            )
        else:
            spy = Put(
                "SPY",
                d=expiry["day"],
                m=expiry["month"],
                y=expiry["year"],
            )
        # find suitable strike
        prop_strike_baseline = (1 + perc_delta_money * scaling) * spy.underlying.price
        spy_strike = find_nearest(list(spy.strikes), prop_strike_baseline)
        spy.set_strike(spy_strike)

        baseline_option = Option.from_ws_obj(spy)
        baseline_metrics = Metrics(baseline_option)

        return baseline_option, baseline_metrics

    @staticmethod
    def extract_contract(spec_str: str) -> tuple[dict, str]:
        spec_list = spec_str.split(" ")

        ticker = spec_list[0]
        expiry = spec_list[1]
        strike = spec_list[-1][:-1]
        contract_type = spec_str[-1]

        try:
            month, day, year = expiry.split("-")
            expiry = {"month": month, "day": day, "year": year}
        except ValueError:
            print(f"Incorrect data format for date {expiry}, should be MM-DD-YYYY.")

        return ticker, expiry, strike, contract_type


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="compare_options",
        description="Quick script to provide information on derivatives.",
    )

    parser.add_argument(
        "contr_name",
        help=(
            "Provide the contr_name specs in standard syntax. For example, "
            "a Call option for SPY at strike price $400 for expiration 06/16/2022 "
            "should be input as `'SPY 06-16-2023 400C'`. Note the quotation marks."
        ),
    )
    parser.add_argument(
        "-b",
        "--baseline",
        help=(
            "Writes a baseline options contract to compare the input contract against. "
            "The baseline contract is from $SPY at the same expiry and a strike at "
            "the same proportion of moniness as the given options contract. For example, "
            "if the specified contract is 20%% Out of the Money, the baseline contract "
            "will also be 20%% Out of the Money."
        ),
        action="store_true",
    )
    parser.add_argument(
        "-s",
        "--scaling",
        help=(
            "Often times, the proportion of moniness of the specified contract does not "
            "match up against a $SPY contract with the same proportion. For example, "
            "if the proportion of the input contract is 20%%, the same proportion is "
            "applied to $SPY. But a $SPY contract 20%% Out of the Money is often times "
            "much more unlikely than the input contract."
        ),
        type=float,
        default=0.5,
    )
    args = parser.parse_args()

    Process(args.contr_name, args.baseline, args.scaling)
