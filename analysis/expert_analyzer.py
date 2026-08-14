from config.expert_sources import EXPERT_SOURCES

from providers.travcash_provider import TravcashProvider
from providers.rekatochklart_provider import RekatochklartProvider


class ExpertAnalyzer:

    #
    # Hamtar experttips fran flera kallor (Travcash,
    # Rekatochklart, fler kan laggas till) och raknar ut ett
    # Expert Index per hast: hur stor andel av kallorna som
    # pekar ut just den hasten i det loppet.
    #
    # Anvands sedan som en komponent i CrowdEngine (motsvarar
    # "Experttips" i KAMT-modellens Crowd Index).
    #
    # Till skillnad fran de andra analysmodulerna kors den
    # har inte per lopp via register_modules, eftersom tipsen
    # hamtas en gang per spel (inte en gang per delopp) for
    # att undvika onodiga natverksanrop. collect_tips() kors
    # forst for hela spelet, sedan apply() per lopp.
    #

    name = "Expertanalys"

    def __init__(self):

        self.travcash = TravcashProvider()
        self.rekatochklart = RekatochklartProvider()

    def collect_tips(self, game_id):

        sources = EXPERT_SOURCES.get(game_id)

        if not sources:
            print(
                f"[Expertanalys] Inga kallor konfigurerade for "
                f"game_id '{game_id}' i config/expert_sources.py "
                f"- experttips hoppas over."
            )
            return {}

        tips_by_race = {}

        if "travcash_slug" in sources:

            try:

                travcash_tips = self.travcash.collect(
                    sources["travcash_slug"]
                )

                self._merge(tips_by_race, "travcash", travcash_tips)

            except Exception as e:
                print(f"[Expertanalys] Kunde inte hamta Travcash: {e!r}")

        if "rekatochklart_url" in sources:

            try:

                reka_tips = self.rekatochklart.collect(
                    sources["rekatochklart_url"]
                )

                self._merge(tips_by_race, "rekatochklart", reka_tips)

            except Exception as e:
                print(
                    f"[Expertanalys] Kunde inte hamta "
                    f"Rekatochklart: {e!r}"
                )

        if tips_by_race:
            print(
                f"[Expertanalys] Hamtade experttips for "
                f"{len(tips_by_race)} lopp fran "
                f"{len(sources)} kalla/kallor."
            )

        return tips_by_race

    @staticmethod
    def _merge(target, source_name, tips_by_leg_label):

        for leg_label, numbers in tips_by_leg_label.items():

            race_number = int(leg_label.split("-")[-1])

            target.setdefault(race_number, {})[source_name] = numbers

    def apply(self, race, leg_index, tips_by_race):

        #
        # OBS: race.race_number ar ATG:s absoluta loppnummer
        # for dagen pa banan (t.ex. lopp 3-10), INTE vilket
        # delopp (1-8) det ar inom sjalva V85-omgangen. Tips-
        # kallorna numrerar sina lopp efter position inom
        # omgangen ("V85-1".."V85-8"), sa vi maste matcha mot
        # leg_index (racets position i analysis_data.races)
        # istallet for race.race_number.
        #

        leg_tips = tips_by_race.get(leg_index)

        if not leg_tips:

            #
            # Inga experttips insamlade for det har loppet -
            # lamna expert_index osatt (CrowdEngine hanterar
            # det genom att inte rakna in komponenten alls).
            #

            return

        total_sources = len(leg_tips)

        for horse in race.horses:

            mentions = sum(
                1
                for numbers in leg_tips.values()
                if horse.number in numbers
            )

            expert_index = round(100 * mentions / total_sources, 1)

            horse.set_metric("expert_index", expert_index)
