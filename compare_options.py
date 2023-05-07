# Author: Austin Benny

from datetime import datetime

import numpy as np
from wallstreet import Call, Put

from jinja2 import Environment, FileSystemLoader

class CompareContracts:
    def __init__(self, contr_name:str):
        # Extract conntract identifiers from input contract string
        ticker,strike,expiry,contract_type = self.extract_contract(contr_name)

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
                ("Incorrectly specified contr_name type "
                f"[{contract_type}] in input string [{contr_name}].")
            )

        # Assign contract name attribute after error checking
        self.contr_name = contr_name
        # make option dictionary
        self.option = {
            "ticker": ticker.upper(),
            "strike": float(strike),
            "expiry": {k:int(v) for k,v in expiry.items()},
            "contract_type": contract_type.upper(),
        }

        self._add_option_parameters(self.option)
        self.metrics = self._calculate_metrics()
        self._write_metrics()

    def _write_metrics(self):
        # TODO: Use jinja
        # TODO: Better output

        perc_delta_money = (
            (self.option['strike'] - self.option["underlying_price"]) / self.option["underlying_price"]
        )
        (
            baseline_name,
            baseline_option,
            baseline_metrics
        ) = self._get_baseline_option(perc_delta_money, scaling=0.5)

        # combine dicts, feed to template

        environment = Environment(loader=FileSystemLoader("templates/"))
        template = environment.get_template("compare_output.txt")

        out_str = template.render()

        print(out_str)

    def _calculate_metrics(self) -> dict[float]:
        metrics = {}

        metrics["ask_bid_spread"] = self.option["ask"] - self.option["bid"]
        metrics["ask_bid_perc_diff"] = (
            metrics["ask_bid_spread"] / ((self.option["ask"] + self.option["bid"]) / 2)
        )
        if self.option['strike'] < self.option["underlying_price"]:
            metrics["extrensic_value"] = (
                self.option["premium"] - (self.option["underlying_price"] - self.option['strike'])
            )
        else:
            metrics["extrensic_value"] = self.option["premium"]
        metrics["sample_perc_change"] = 0.01
        metrics["delta_change"] = (
            self.option["delta"] * self.option["underlying_price"] * metrics["sample_perc_change"]
        )
        metrics["contr_perc_change"] = metrics["delta_change"] / self.option["premium"]
        metrics["iv_change"] = self.option["vega"] / self.option["premium"]
        metrics["non_dim_iv"] = metrics["iv_change"] / self.option["iv"]
        metrics["theta_change"] = self.option["theta"] / self.option["premium"]
        metrics["break_even"] = metrics["theta_change"] * self.option["premium"] \
            * (1 / self.option["underlying_price"] * self.option["delta"])
        metrics["delta_prem"] = self.option["delta"] / self.option["premium"]
        metrics["gamma_del"] = self.option["gamma"] / self.option["delta"]
        metrics["ext_theta"] = metrics["extrensic_value"] / self.option["theta"]

        return metrics

    @staticmethod
    def _add_option_parameters(option:dict[str, float, dict]):

        if option["contract_type"] == "P":
            ws_contr = Put(
                option["ticker"],
                strike=option["strike"],
                d=option["expiry"]["day"],
                m=option["expiry"]["month"],
                y=option["expiry"]["year"],
            )
        else:
            ws_contr = Call(
                option["ticker"],
                strike=option["strike"],
                d=option["expiry"]["day"],
                m=option["expiry"]["month"],
                y=option["expiry"]["year"],
            )

        option["premium"] = float(ws_contr.price)
        option["underlying_price"] = float(ws_contr.underlying.price)
        option["delta"] = float(ws_contr.delta())
        option["theta"] = float(ws_contr.theta())
        option["gamma"] = float(ws_contr.gamma())
        option["vega"] = float(ws_contr.vega())
        option["iv"] = float(ws_contr.implied_volatility())
        option["bid"] = float(ws_contr.bid)
        option["ask"] = float(ws_contr.ask)

    def _get_baseline_option(self, perc_delta_money, scaling):
        def find_nearest(array, value):
            array = np.asarray(array)
            idx = (np.abs(array - value)).argmin()

            return array[idx]

        ws_contr = Call(
            "SPY",
            d=self.option["expiry"]["day"],
            m=self.option["expiry"]["month"],
            y=self.option["expiry"]["year"],
        )
        # find suitable strike
        prop_strike_baseline = (1 + perc_delta_money * scaling) * ws_contr.underlying.price
        spy_strike = find_nearest(list(ws_contr.strikes), prop_strike_baseline)

        baseline_option = {
            "ticker": 'SPY',
            "strike": float(spy_strike),
            "expiry": self.option['expiry'],
            "contract_type": self.option['contract_type'],
        }

        self._add_option_parameters(baseline_option)
        baseline_metrics = self._calculate_metrics(baseline_option)

        spy_contr_name = (
            f"SPY "
            f"{self.option['expiry']['month']}-{self.option['expiry']['day']}-{self.option['expiry']['year']} "
            f"{spy_strike}{self.option['contract_type']}"
        )

        return spy_contr_name, baseline_option, baseline_metrics

    @staticmethod
    def extract_contract(spec_str: str) -> tuple(dict, str):
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
        "contr_name",
        help=(
            "Provide the contr_name specs in standard syntax. For example, "
            "a Call option for SPY at strike price $400 for expiration 06/16/2022 "
            "should be input as `'SPY 06-16-2023 400C'`. Note the quotation marks."
        ),
    )
    args = parser.parse_args()

    CompareContracts(args.contr_name)
