import math
from datetime import datetime
from internal.site.paybyphone.parkingZone import ParkingZone


class ParkingOptimizer:

    def __init__(
        self,
        step_minutes: int,
        parkingZone: ParkingZone,
        allow_free_quota_once: bool = True,
    ):
        self.parkingZone = parkingZone
        self.step = step_minutes
        self.allow_free_quota_once = allow_free_quota_once
        self._price_cache: dict[int, float] = {}
        self._single_ticket_quotes: dict[int, float] = {}
        self.promo_duration: int = 0  # Ex: 30 minutes offertes 1 fois

    def fetch_tariffs(self, durations: list[int] | None = None) -> None:
        """Récupère les tarifs réels et alimente le cache avec des tarifs répétables sans promo."""
        if not self.parkingZone.ratePolicyId or self.parkingZone.maxStay == 0:
            self.parkingZone.getRestrictionOnZone()

        if durations is None:
            durations = list(
                range(self.step, self.parkingZone.maxStay + 1, self.step)
            )

        for d in durations:
            try:
                real_dur, cost, promo_dur, promo_usage = (
                    self.parkingZone.getQuote(d)
                )

                # Enregistrement du coût brut d'un ticket unique pour cette durée
                self._single_ticket_quotes[d] = cost
                if real_dur not in self._single_ticket_quotes:
                    self._single_ticket_quotes[real_dur] = cost

                if promo_dur > 0 and promo_usage == "Quota":
                    if promo_dur > self.promo_duration:
                        self.promo_duration = promo_dur

                    # Le coût payé correspond à (durée totale - durée promo)
                    paid_duration = real_dur - promo_dur
                    if paid_duration > 0:
                        if (
                            paid_duration not in self._price_cache
                            or cost < self._price_cache[paid_duration]
                        ):
                            self._price_cache[paid_duration] = cost
                else:
                    # Ticket standard sans promotion
                    if (
                        real_dur not in self._price_cache
                        or cost < self._price_cache[real_dur]
                    ):
                        self._price_cache[real_dur] = cost

            except Exception:
                # Ignore les dépassements de plafonds ou tranches non autorisées
                pass

    def _solve_dp(
        self, target_minutes: int
    ) -> dict[str, float | list[int] | int]:
        """Trouve la combinaison optimale de tickets payants pour couvrir au moins target_minutes."""
        if target_minutes <= 0:
            return {"total_cost": 0.0, "tickets": [], "covered_minutes": 0}

        valid_durations = sorted(self._price_cache.keys(), reverse=True)
        if not valid_durations:
            raise ValueError("Aucun tarif disponible en cache.")

        search_limit = target_minutes + max(valid_durations)

        # min_cost[m] = coût minimal pour couvrir m minutes
        min_cost = [float("inf")] * (search_limit + 1)
        # min_tickets[m] = nombre minimal de tickets pour obtenir ce coût à m minutes
        min_tickets = [float("inf")] * (search_limit + 1)
        # best_split[m] = durée du ticket utilisé
        best_split = [0] * (search_limit + 1)

        min_cost[0] = 0.0
        min_tickets[0] = 0

        # Résolution par programmation dynamique
        for m in range(1, search_limit + 1):
            for d in valid_durations:
                if d <= m and min_cost[m - d] != float("inf"):
                    cost = min_cost[m - d] + self._price_cache[d]
                    ticket_count = min_tickets[m - d] + 1

                    # Condition : moins cher, OU même prix avec moins de tickets
                    if cost < min_cost[m] or (
                        math.isclose(cost, min_cost[m], abs_tol=1e-4)
                        and ticket_count < min_tickets[m]
                    ):
                        min_cost[m] = cost
                        min_tickets[m] = ticket_count
                        best_split[m] = d

        # Sélection de la meilleure cible >= target_minutes
        best_target = None
        lowest_cost = float("inf")
        fewest_tickets = float("inf")

        for m in range(target_minutes, search_limit + 1):
            cost = min_cost[m]
            count = min_tickets[m]

            if cost < lowest_cost:
                lowest_cost = cost
                fewest_tickets = count
                best_target = m
            elif math.isclose(cost, lowest_cost, abs_tol=1e-4):
                if count < fewest_tickets:
                    fewest_tickets = count
                    best_target = m

        if best_target is None or lowest_cost == float("inf"):
            raise ValueError(
                f"Impossible de couvrir au moins {target_minutes} minutes."
            )

        # Reconstitution de la liste des tickets
        tickets = []
        curr = best_target
        while curr > 0:
            d = best_split[curr]
            tickets.append(d)
            curr -= d

        return {
            "total_cost": round(lowest_cost, 2),
            "tickets": tickets,
            "covered_minutes": best_target,
        }

    def get_single_ticket_cost(self, duration_minutes: int) -> float:
        """Calcule le tarif qu'un utilisateur paierait pour un seul ticket couvrant duration_minutes."""
        if duration_minutes <= 0:
            return 0.0

        max_stay = self.parkingZone.maxStay or 1125

        if duration_minutes > max_stay:
            nb_full = duration_minutes // max_stay
            rem = duration_minutes % max_stay
            cost_full = self.get_single_ticket_cost(max_stay)
            cost_rem = self.get_single_ticket_cost(rem) if rem > 0 else 0.0
            return round(nb_full * cost_full + cost_rem, 2)

        # 1. Si le quota gratuit est activé (comportement d'un ticket unique normal sur PayByPhone)
        if self.allow_free_quota_once:
            if duration_minutes in self._single_ticket_quotes:
                return self._single_ticket_quotes[duration_minutes]
            try:
                _, cost, _, _ = self.parkingZone.getQuote(duration_minutes)
                self._single_ticket_quotes[duration_minutes] = cost
                return cost
            except Exception:
                pass

        # 2. Si le quota gratuit n'est pas autorisé (tarif plein sans promotion)
        if not self.allow_free_quota_once:
            if duration_minutes in self._price_cache:
                return self._price_cache[duration_minutes]
            target_with_promo = duration_minutes + self.promo_duration
            if target_with_promo in self._single_ticket_quotes:
                return self._single_ticket_quotes[target_with_promo]
            try:
                if self.promo_duration > 0 and (duration_minutes + self.promo_duration) <= max_stay:
                    _, cost_without, _, _ = self.parkingZone.getQuote(duration_minutes + self.promo_duration)
                    return cost_without
            except Exception:
                pass

        if duration_minutes in self._single_ticket_quotes:
            return self._single_ticket_quotes[duration_minutes]

        if duration_minutes in self._price_cache:
            return self._price_cache[duration_minutes]

        return 0.0

    def optimize(
        self,
        start_time: str | None = None,
        end_time: str | None = None,
        duration_minutes: int | None = None,
    ) -> dict[str, float | list[int] | int | dict | bool]:
        # 1. Calcul de la durée demandée
        if duration_minutes is not None:
            raw_minutes = duration_minutes
        elif start_time and end_time:
            t1 = datetime.strptime(start_time, "%H:%M")
            t2 = datetime.strptime(end_time, "%H:%M")
            raw_minutes = int((t2 - t1).total_seconds() // 60)
        else:
            raise ValueError(
                "Fournir soit start_time et end_time, soit duration_minutes."
            )

        if raw_minutes <= 0:
            return {
                "total_cost": 0.0,
                "tickets": [],
                "covered_minutes": 0,
                "single_ticket_cost": 0.0,
                "has_promo": False,
                "without_promo": {"total_cost": 0.0, "tickets": [], "covered_minutes": 0},
            }

        target_minutes = math.ceil(raw_minutes / self.step) * self.step

        # Coût standard pour un seul ticket couvrant la durée cible
        single_cost = self.get_single_ticket_cost(target_minutes)

        # Résolution de l'option 100% payante (sans promotion)
        option_paid = self._solve_dp(target_minutes)

        has_promo = False
        # Si l'utilisation du quota gratuit est activée et qu'un quota existe
        if self.allow_free_quota_once and self.promo_duration > 0:
            remaining_minutes = max(0, target_minutes - self.promo_duration)

            if remaining_minutes == 0:
                option_promo = {
                    "total_cost": 0.0,
                    "tickets": [self.promo_duration],
                    "covered_minutes": self.promo_duration,
                }
            else:
                rem_target = (
                    math.ceil(remaining_minutes / self.step) * self.step
                )
                rem_solution = self._solve_dp(rem_target)
                option_promo = {
                    "total_cost": rem_solution["total_cost"],
                    "tickets": [self.promo_duration] + rem_solution["tickets"],
                    "covered_minutes": (
                        self.promo_duration + rem_solution["covered_minutes"]
                    ),
                }

            # Comparaison avec l'option 100% payante
            if option_promo["total_cost"] <= option_paid["total_cost"]:
                best = option_promo
                has_promo = True
            else:
                best = option_paid
                has_promo = False
        else:
            best = option_paid
            has_promo = False

        # Si l'achat d'un seul ticket est moins cher ou égal
        if single_cost > 0 and single_cost < best["total_cost"]:
            best = {
                "total_cost": single_cost,
                "tickets": [target_minutes],
                "covered_minutes": target_minutes,
            }
            has_promo = self.allow_free_quota_once and self.promo_duration > 0

        return {
            "total_cost": best["total_cost"],
            "tickets": best["tickets"],
            "covered_minutes": best["covered_minutes"],
            "single_ticket_cost": single_cost,
            "has_promo": has_promo,
            "without_promo": option_paid,
        }