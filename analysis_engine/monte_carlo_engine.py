import random


class MonteCarloEngine:
    #
    # KAMT v2, Niva 3 (generellt Lager 2-komponent, se
    # 003_Restructuring_Plan.md): kor en given scenario-funktion
    # ett antal ganger och aggregerar utfallen till en
    # sannolikhetsfordelning.
    #
    # Kanner INTE till trav, hastar, matriser eller nagon
    # domanlogik - det ar Lager 3:s ansvar att tillhandahalla
    # scenario_fn. Samma motor ska kunna aterranvandas av
    # framtida moduler (fotboll, aktiemarknad) med en helt
    # annan scenario-funktion.
    #

    def __init__(self, n_simulations=10000, random_seed=None):
        self.n_simulations = n_simulations
        self._rng = random.Random(random_seed)

    def run(self, scenario_fn):
        #
        # scenario_fn: (rng) -> nagon hashable identifierare for
        # "vinnaren" av en enskild simulering, eller None om
        # simuleringen inte gav nagon vinnare (t.ex. alla
        # deltagare drabbades av ett "incident").
        #
        # Returnerar en dict {identifierare: sannolikhet i procent},
        # baserat pa andelen simuleringar som gav respektive
        # utfall bland de simuleringar som faktiskt gav en vinnare.
        #
        outcomes = {}

        for _ in range(self.n_simulations):
            winner = scenario_fn(self._rng)
            if winner is None:
                continue
            outcomes[winner] = outcomes.get(winner, 0) + 1

        total = sum(outcomes.values())
        if total == 0:
            return {}

        return {
            identifier: round(100 * count / total, 1)
            for identifier, count in outcomes.items()
        }
