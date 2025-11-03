This patch ensures account.payment postings use partner AR/AP as the counterpart,
leaving the liquidity line on the bank/cash account. It also declares depends on
other addons that override the same method so this one loads last.
