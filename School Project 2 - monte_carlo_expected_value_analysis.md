# Monte Carlo Expected Value & Risk Simulation

## Project Overview

This project demonstrates how **expected value (EV)** and **Monte Carlo simulation** can be used to evaluate the financial impact of uncertain operational events.

The original analysis was based on a real-world logistics-style problem. For public use, all company names, customer names, lane identifiers, and potentially sensitive business figures have been removed or replaced with **synthetic example values**.

The goal is to demonstrate the analytical method without disclosing proprietary business information.

---

## What is Monte Carlo?

What is Monte Carlo?

> Monte Carlo (MC) is a simulation method that uses random sampling to estimate numerical quantities—like expected values, probabilities, or full distributions—especially when exact math is difficult or when you want to stress‑test assumptions.

The Idea (One Sentence)

> If you can simulate the uncertain process, then by repeating that simulation many times and averaging, you can estimate the quantity you care about.

How It Works

1) Specify a model for uncertainty (e.g., each load is late with probability p).
2) Simulate one outcome by drawing random values (e.g., mark which loads are late).
3) Compute the metric of interest from that outcome (e.g., total revenue after penalties).
4) Repeat steps 2–3 many times (hundreds to millions).
5) Summarize the results: mean (expected value), standard deviation (volatility), confidence intervals.

Why It Works (Brief Math)
• Law of Large Numbers: the average of many simulations converges to the true expected value.
• Central Limit Theorem: the sampling distribution of the mean is approximately normal; the mean’s standard error is roughly sd/√N, enabling confidence intervals.

When Monte Carlo is Useful
• Closed-form math is messy (tiered penalties, different p_i or fees per load, correlated lateness).
• Scenario testing (change p, fees, policies and re‑simulate).
• Need the whole distribution, not just a single number (e.g., P(total < $12.5k)).

Limitations / Caveats
• Results are only as good as the model (garbage in, garbage out).
• Always approximate; sampling error shrinks as trials increase.
• Rare events may need many trials or variance‑reduction techniques to estimate accurately.

---

## Business Problem

Assume an operation manages a batch of shipments. Each shipment generates baseline revenue, but a fixed service penalty is deducted whenever the shipment arrives late.

Because lateness is uncertain, the analysis asks:

> **What revenue should we expect after accounting for lateness risk, and how much variability could that uncertainty create?**

Each shipment has two possible outcomes:

- **On time:** no penalty is applied.
- **Late:** a fixed penalty is deducted.

Monte Carlo simulation repeats this uncertain process many times to estimate the distribution of possible financial outcomes.

---

## Synthetic Inputs

The following values are intentionally illustrative and are **not production or customer data**.

| Variable | Example Value | Description |
|---|---:|---|
| `n_shipments` | 25 | Number of shipments in the batch |
| `prob_late` | 0.12 | Assumed probability that a shipment is late |
| `late_fee` | $200 | Penalty applied to each late shipment |
| `baseline_revenue` | $20,000 | Synthetic revenue before penalties |
| `n_simulations` | 100,000 | Number of Monte Carlo trials |

---

## 1. Expected Value

Let:

- `R` = revenue associated with a shipment
- `p` = probability of lateness
- `F` = penalty when late

There are two possible outcomes for one shipment:

```text
On time:  R      with probability (1 - p)
Late:     R - F  with probability p
```

Therefore:

```text
EV = R(1 - p) + (R - F)p
```

Expanding:

```text
EV = R - Rp + Rp - Fp
```

The middle terms cancel:

```text
EV = R - pF
```

So:

> **Expected penalty per shipment = probability of lateness × penalty amount.**

This is the core expected-value relationship used throughout the analysis.

---

## 2. Batch-Level Expected Value

For `n` independent shipments with the same lateness probability and penalty:

```text
E[L] = n × p
```

where `L` is the number of late shipments.

Using the synthetic example:

```text
E[L] = 25 × 0.12
     = 3
```

So we expect approximately **3 late shipments per batch**.

Expected total penalty:

```text
E[P] = n × p × F
```

Using the example values:

```text
E[P] = 25 × 0.12 × 200
     = 600
```

Expected risk-adjusted revenue:

```text
EV_total = baseline revenue - expected penalty
         = 20,000 - 600
         = 19,400
```

**Expected risk-adjusted revenue: $19,400**

Expected value gives us the center of the distribution, but it does not describe the **risk around that expectation**. That is where simulation becomes useful.

---

## 3. Theoretical Variability

If each shipment independently has probability `p` of being late, then the number of late shipments follows a binomial distribution:

```text
L ~ Binomial(n, p)
```

The variance of a binomial random variable is:

```text
Var(L) = n × p × (1 - p)
```

Its standard deviation is:

```text
SD(L) = sqrt(n × p × (1 - p))
```

Because each late shipment produces a penalty `F`, the standard deviation of the total penalty—and therefore of total revenue—is:

```text
SD_revenue = F × sqrt(n × p × (1 - p))
```

Using the synthetic example:

```text
SD_revenue = 200 × sqrt(25 × 0.12 × 0.88)
           ≈ $325
```

This theoretical result provides a benchmark against which the Monte Carlo simulation can be validated.

---

## 4. Monte Carlo Simulation

Monte Carlo simulation approximates the range of possible outcomes by repeatedly sampling from the assumed probability model.

For each simulation:

1. Generate the number of late shipments.
2. Calculate the resulting penalty.
3. Subtract the penalty from baseline revenue.
4. Store the simulated revenue.
5. Repeat the process many times.

With 100,000 trials, we obtain an empirical distribution of possible revenue outcomes.

### Python Implementation

```python
import numpy as np

# Synthetic, non-production inputs
N_SHIPMENTS = 25
PROB_LATE = 0.12
LATE_FEE = 200.0
BASELINE_REVENUE = 20_000.0
N_SIMULATIONS = 100_000
RANDOM_SEED = 42

rng = np.random.default_rng(RANDOM_SEED)

# Number of late shipments in each simulated batch
late_counts = rng.binomial(
    n=N_SHIPMENTS,
    p=PROB_LATE,
    size=N_SIMULATIONS,
)

# Convert lateness into financial outcomes
simulated_penalties = late_counts * LATE_FEE
simulated_revenue = BASELINE_REVENUE - simulated_penalties

# Simulation statistics
sim_mean = simulated_revenue.mean()
sim_sd = simulated_revenue.std(ddof=1)

print(f"Simulated mean revenue: ${sim_mean:,.2f}")
print(f"Simulated revenue SD:   ${sim_sd:,.2f}")
```

### Why Use the Binomial Distribution?

Each shipment is modeled as a Bernoulli event:

```text
Late_i = 1  with probability p
Late_i = 0  with probability (1 - p)
```

The total number of late shipments is the sum of those Bernoulli events. Under the assumptions of independence and a constant probability of lateness, that total follows a **binomial distribution**.

Using `rng.binomial()` is more efficient than generating every individual shipment outcome when the only required quantity is the total number of late shipments.

---

## 5. Validate Simulation Against Theory

A strong Monte Carlo workflow should not simply generate random numbers. When a closed-form theoretical result exists, the simulation should be checked against it.

```python
expected_late = N_SHIPMENTS * PROB_LATE
expected_penalty = expected_late * LATE_FEE
theoretical_ev = BASELINE_REVENUE - expected_penalty

theoretical_sd = (
    LATE_FEE
    * np.sqrt(N_SHIPMENTS * PROB_LATE * (1 - PROB_LATE))
)

print(f"Theoretical EV: ${theoretical_ev:,.2f}")
print(f"Simulation EV:  ${sim_mean:,.2f}")

print(f"Theoretical SD: ${theoretical_sd:,.2f}")
print(f"Simulation SD:  ${sim_sd:,.2f}")
```

With a sufficiently large number of simulations, the simulated mean and simulated standard deviation should be close to their theoretical counterparts.

That comparison provides a basic **model validation check**.

---

## 6. Monte Carlo Confidence Interval for the Mean

The simulation itself has sampling error because it uses a finite number of trials.

The estimated standard error of the simulated mean is:

```text
SE = s / sqrt(N)
```

where:

- `s` = simulated standard deviation
- `N` = number of simulation trials

An approximate 95% confidence interval for the **Monte Carlo estimate of the mean** is:

```text
mean ± 1.96 × SE
```

Python implementation:

```python
standard_error = sim_sd / np.sqrt(N_SIMULATIONS)

mc_mean_ci = (
    sim_mean - 1.96 * standard_error,
    sim_mean + 1.96 * standard_error,
)

print(
    "95% CI for simulated mean: "
    f"[${mc_mean_ci[0]:,.2f}, ${mc_mean_ci[1]:,.2f}]"
)
```

### Important Distinction

This confidence interval describes **uncertainty in the estimated mean caused by Monte Carlo sampling**.

It is **not** the same thing as the range containing 95% of possible operational outcomes.

For risk analysis, distribution percentiles are often more useful.

---

## 7. Distribution-Based Risk Metrics

Monte Carlo simulation becomes especially useful when we examine the full distribution rather than only its mean.

```python
p05, p50, p95 = np.percentile(
    simulated_revenue,
    [5, 50, 95],
)

print(f"5th percentile:  ${p05:,.2f}")
print(f"Median:          ${p50:,.2f}")
print(f"95th percentile: ${p95:,.2f}")
```

These metrics help answer questions such as:

- What does a relatively poor outcome look like?
- What is the median simulated result?
- What does a relatively strong outcome look like?
- How wide is the distribution of plausible outcomes?

We can also estimate the probability of falling below a business threshold.

```python
REVENUE_THRESHOLD = 19_000

prob_below_threshold = np.mean(
    simulated_revenue < REVENUE_THRESHOLD
)

print(
    f"P(revenue < ${REVENUE_THRESHOLD:,.0f}) = "
    f"{prob_below_threshold:.2%}"
)
```

This converts the simulation into a decision-support metric:

```text
P(revenue < threshold)
```

That probability can often be more actionable than simply reporting average revenue.

---

## 8. Scenario Analysis

One advantage of Monte Carlo simulation is that model assumptions can be changed easily.

For example, we can examine how expected revenue changes as lateness risk increases.

```python
for probability in [0.05, 0.10, 0.15, 0.20, 0.25]:
    late_counts = rng.binomial(
        n=N_SHIPMENTS,
        p=probability,
        size=N_SIMULATIONS,
    )

    revenue = (
        BASELINE_REVENUE
        - late_counts * LATE_FEE
    )

    print(
        f"Late probability: {probability:>5.0%} | "
        f"Mean revenue: ${revenue.mean():,.2f}"
    )
```

This makes it possible to stress-test assumptions such as:

- Higher or lower lateness probabilities
- Different penalty structures
- Larger shipment volumes
- Different revenue thresholds
- Changes in service-level performance

---

## 9. What Monte Carlo Adds Beyond Expected Value

For this simplified example, expected value can be calculated exactly:

```text
EV_total = revenue - n × p × F
```

So Monte Carlo is **not necessary merely to calculate the average expected result**.

Its value is that the same framework can be extended to situations where the analytical solution becomes more difficult, or where decision-makers care about the **entire outcome distribution** rather than only the mean.

Examples include:

- Different lateness probabilities for individual shipments
- Different penalty amounts
- Tiered service penalties
- Weather-dependent delays
- Correlated shipment failures
- Variable shipment revenue
- Capacity constraints
- Multiple interacting risk factors
- Tail-risk probabilities

In those cases, simulation can provide information that a single expected-value calculation cannot.

---

## 10. Assumptions

The simplified model assumes:

1. Each shipment has the same probability of being late.
2. Shipment outcomes are independent.
3. Every late shipment receives the same penalty.
4. Baseline revenue is fixed.
5. The lateness probability is known and constant.

These assumptions are intentionally simple.

In a production model, they should be tested against historical data and replaced with more realistic distributions or dependencies when appropriate.

For example, weather or network congestion may cause several shipments to become late simultaneously, violating the independence assumption.

---

## 11. Limitations

Monte Carlo simulation does not eliminate uncertainty.

Its output is only as reliable as the assumptions used to construct the model.

Key limitations include:

- Incorrect probability assumptions produce misleading results.
- Correlated risks require more sophisticated modeling.
- Rare events may require substantially more simulations.
- Simulation results should be validated whenever theoretical or historical benchmarks exist.
- A large number of trials reduces simulation error but does not correct a poorly specified model.

---

## 12. Key Takeaways

This project demonstrates proficiency with:

- Expected-value modeling
- Bernoulli and binomial probability
- Monte Carlo simulation
- NumPy random-number generation
- Reproducible simulation using random seeds
- Theoretical vs. simulated model validation
- Standard deviation and uncertainty measurement
- Monte Carlo confidence intervals
- Distribution percentiles
- Threshold-probability estimation
- Scenario and sensitivity analysis
- Translating probabilistic results into business risk metrics

### Analytical Workflow

```text
Define uncertainty
      ↓
Build probability model
      ↓
Derive theoretical benchmark
      ↓
Simulate thousands of scenarios
      ↓
Measure outcome distribution
      ↓
Validate simulation
      ↓
Calculate risk probabilities
      ↓
Stress-test assumptions
      ↓
Support decisions
```
---

## Technologies

- Python
- NumPy
- Probability & Statistics
- Monte Carlo Simulation
- Expected Value Analysis
- Risk Modeling
