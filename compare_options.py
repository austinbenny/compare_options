# Author: Austin Benny

import re
import datetime
import yfinance as yf


class compareContracts:
    def __init__(self, ticker, month, day, year, strike, cType):
        self.ticker = ticker
        self.strike = strike
        self.day = day
        self.month = month
        self.year = year
        self.cType = cType

        self.build()

    def build(self):
        self.GetOpt()
        self.DoCalcs()
        self.writeCSV()
        self.write()

    @staticmethod
    def ratioInIndex(var1, var2):
        """converts the ratios into an index between 0 and 100 kinda like the RSI"""
        return 100 - (100 / (1 + (var1 / var2)))

    def writeCSV(self):
        pass

    def write(self):
        x = datetime.datetime.now()
        date = x.strftime("%x") + " " + x.strftime("%a")

        # write to CSV

        self.optStr = "\n__________________\n"
        self.optStr += (
            self.ticker
            + " "
            + str(self.month)
            + "/"
            + str(self.day)
            + "/"
            + str(self.year)
            + " "
            + str(self.strike)
            + self.short
            + " [Run on: "
            + date
            + "]"
            + "\n"
        )
        self.optStr += "__________________\n"
        self.optStr += "{:.0%} move in ${:12} = {:.2%} move in option\n".format(
            self.percentChange, self.ticker, self.optionpercentChange
        )
        self.optStr += "1 day move in ${:9} = {:.2%} decrease in option\n".format(
            self.ticker, self.thetaChange
        )
        self.optStr += "To earn money ${:9} > {:.2%} move per day\n".format(
            self.ticker, self.breakEven
        )
        self.optStr += "{:.0%} IV move in ${:9} = {:.2%} move in option\n".format(
            self.percentChange, self.ticker, self.ivChange
        )
        self.optStr += "delta/premium            = {:.2f} [index: {:.3f}]\n".format(
            self.deltaPrem, self.d_p_index
        )
        self.optStr += "gamma/delta              = {:.2f} [index: {:.3f}]\n".format(
            self.gammaDel, self.g_d_index
        )
        self.optStr += "extrinsicValue/theta     = {:.2f} [index: {:.3f}]\n".format(
            self.extTheta, self.e_t_index
        )
        self.optStr += "premium per (vega/IV)    = {:.2f} [index: {:.3f}]\n".format(
            self.nonDimIV, self.nonDimIV_index
        )
        self.optStr += "ask-bid spread           = {:.2f} [% diff: {:.0%}]\n".format(
            self.ask - self.bid, self.percDiff
        )
        self.optStr += "premium                  = ${:.2f}\n".format(self.premium)
        self.optStr += "__________________\n"

        print(self.optStr)

        with open("script_output/_compareOptionsLog.txt", "a") as log:
            log.write(self.optStr)

    def DoCalcs(self):
        self.percentChange = 0.01
        deltaChange = self.delta * self.price * self.percentChange
        self.optionpercentChange = deltaChange / self.premium

        self.ivChange = self.vega / self.premium
        self.nonDimIV = self.ivChange / self.iv
        self.thetaChange = self.theta / self.premium
        self.breakEven = (self.thetaChange * self.premium) / (self.price * self.delta)
        self.deltaPrem = self.delta / self.premium
        self.gammaDel = self.gamma / self.delta
        self.extTheta = self.extrensicVal / self.theta

        # indexes
        self.g_d_index = self.ratioInIndex(self.gamma, self.delta)
        self.d_p_index = self.ratioInIndex(self.delta, self.premium)
        self.e_t_index = self.ratioInIndex(self.extrensicVal, self.theta)
        self.nonDimIV_index = self.ratioInIndex(self.ivChange, self.iv)

    def GetOpt(self):
        if self.cType == "Y":
            self.cType = "Call"
            self.short = "C"
            try:
                from wallstreet import Call as Type
            except:
                print("ERROR:Install wallstreet using pip install wallstreet")

        elif self.cType == "N":
            self.cType = "Put"
            self.short = "P"
            try:
                from wallstreet import Put as Type
            except:
                print('ERROR:Install wallstreet using "pip install wallstreet"')

        if len(str(self.year)) == 2:
            self.year = int("20" + str(self.year))

        # if (self.year != int(datetime.datetime.now().year)) or (self.year != int(datetime.datetime.now().year + 1)):
        #     self.year = int(datetime.datetime.now().year)

        print(type(self.ticker), self.day, self.month, self.year, self.strike)

        try:
            self.opt = Type(self.ticker, self.day, self.month, self.year, self.strike)
        except:
            print("ERROR:One or more options fundamentals is wrong")

        self.premium = float(self.opt.price)
        self.price = float(self.opt.underlying.price)
        self.delta = float(self.opt.delta())
        self.theta = float(self.opt.theta())
        self.gamma = float(self.opt.gamma())
        self.vega = float(self.opt.vega())
        self.iv = float(self.opt.implied_volatility())
        self.bid = float(self.opt.bid)
        self.ask = float(self.opt.ask)

        self.percDiff = float((self.ask - self.bid) / ((self.ask + self.bid) / 2))

        if self.strike < self.price:
            self.extrensicVal = self.premium - (self.price - self.strike)
        else:
            self.extrensicVal = self.premium


if __name__ == "__main__":

    def specChar(string):
        regex = re.compile("[@_!#$%^&*()<>?/\|}{~:]")
        if regex.search(string) == None:
            return False
        else:
            return True

    analysis = 2

    if analysis == 1:
        while True:
            try:
                ticker = str(input("Stock = "))
                ticker = ticker.upper()
            except:
                print("ERROR: Ticker input not string")
                continue

            if (ticker.isalpha() == False) or (specChar(ticker) == True):
                print("ERROR: Ticker cannot have numbers or special chars")
                continue
            else:
                break

        while True:
            try:
                month = int(input("exp. month = "))
            except:
                print("ERROR: exp. month is not int")
                continue

            if isinstance(month, float):
                print("ERROR: exp. month cannot be float, int required")
                continue
            else:
                break

        while True:
            try:
                day = int(input("exp. day = "))
            except:
                print("ERROR: exp. day is not int")
                continue

            if isinstance(day, float):
                print("ERROR: exp. day cannot be float, int required")
                continue
            else:
                break

        while True:
            try:
                year = int(input("exp. year = "))
            except:
                print("ERROR: exp. year is not int")
                continue

            if isinstance(year, float):
                print("ERROR: exp. year cannot be float, int required")
                continue
            else:
                break

        while True:
            try:
                strike = float(input("strike = "))
                strike = int(strike)
            except:
                print("ERROR: Strike has to be wither float or int")
                continue
            else:
                break

        while True:
            try:
                cType = str(input("Are these calls? [Y/N]:"))
            except:
                print("ERROR: contract type has to be string")
                continue

            cType = cType.upper()
            if (cType != "Y") and (cType != "N"):
                print("ERROR: contract type ans. has to be either y/n")
                continue
            else:
                break

        compareContracts(ticker, month, day, year, strike, cType)

    else:
        compareContracts("DKNG", 9, 17, 2021, 60, "Y")
