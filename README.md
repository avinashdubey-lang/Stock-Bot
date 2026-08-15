# Stock Trading Engine

An event-driven automated intraday trading engine built in Python.

The project evolved from strategy development and historical backtesting into a
complete end-to-end trading system capable of processing real-time market data,
generating trading signals, applying risk controls, executing paper or live
orders, monitoring positions, logging trades, and managing the trading-session
lifecycle.

The system supports both **paper trading** and **live trading** through
Angel One SmartAPI.


## Overview

The goal of this project was not simply to automate a trading strategy.

The goal was to build a modular system that could take a trading decision
through the complete lifecycle:

```text
Market Data
     ↓
Candle Construction
     ↓
Strategy
     ↓
Signal
     ↓
Risk Validation
     ↓
Order Execution
     ↓
Position Monitoring
     ↓
Trade Logging
     ↓
Session Shutdown
```

The engine separates market data, strategy logic, risk management, execution,
broker integration, logging, and session management into independent
components.

This separation makes it possible to test and evolve individual parts of the
system without coupling the entire trading pipeline to a single script.


## Architecture

The engine is organized as a modular event-driven pipeline. Each component has
a specific responsibility, while the execution layer coordinates the overall
trading flow.

```text
                         ┌─────────────────┐
                         │   Angel One API │
                         └────────┬────────┘
                                  │
                           Live Market Data
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    LiveFeed     │
                         └────────┬────────┘
                                  │
                              Live Ticks
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  CandleBuilder  │
                         └────────┬────────┘
                                  │
                           Completed Candle
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     Strategy    │
                         └────────┬────────┘
                                  │
                               Signal
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ ExecutionEngine │
                         └────────┬────────┘
                                  │
                            Risk Validation
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   RiskManager   │
                         └────────┬────────┘
                                  │
                              Approved
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     Broker      │
                         └────────┬────────┘
                                  │
                         ┌────────┴────────┐
                         │                 │
                         ▼                 ▼
                  ┌──────────────┐  ┌──────────────┐
                  │  PaperBroker │  │  AngelBroker │
                  └──────────────┘  └──────────────┘
                         │                 │
                         └────────┬────────┘
                                  │
                            Trade Result
                                  │
                         ┌────────┴────────┐
                         │                 │
                         ▼                 ▼
                  ┌────────────┐   ┌───────────────┐
                  │TradeLogger │   │TradingSession │
                  └────────────┘   └───────────────┘
```

### Component Flow

**LiveFeed**

Receives real-time market ticks from the broker's WebSocket feed.

**CandleBuilder**

Aggregates incoming ticks into completed timeframe candles that can be
consumed by the strategy.

**Strategy**

Processes completed candles and determines whether the current market state
produces a trading signal.

**ExecutionEngine**

Coordinates signals, risk checks, position state, order execution, and exit
handling.

**RiskManager**

Validates whether a generated signal is allowed to result in a trade based on
the configured risk controls.

**Broker**

Provides the execution interface. The system can route execution through
either a simulated paper broker or the live Angel One broker implementation.

**TradeLogger**

Records trade activity and execution results for later analysis.

**TradingSession**

Manages the lifecycle and state of the trading session, including session
startup, daily state, and end-of-day shutdown.


## Live Data & Execution Flow

The engine processes market data through two complementary paths: a
**candle-driven signal path** for strategy decisions and a **live-price
monitoring path** for managing open positions.

### Entry Pipeline

Completed candles are passed to the strategy for signal generation.

```text
Live Tick
    ↓
LiveFeed
    ↓
CandleBuilder
    ↓
Completed Candle
    ↓
Strategy
    ↓
Entry Signal
    ↓
ExecutionEngine
    ↓
RiskManager
    ↓
Broker
```

The strategy operates on completed candles rather than incomplete candle data.
This keeps signal generation deterministic and prevents an unfinished candle
from being treated as a confirmed market condition.

### Position Monitoring & Exit Pipeline

Once a position is open, the execution layer can monitor live market prices
for exit conditions.

```text
Live Tick
    ↓
ExecutionEngine
    ↓
Position Monitoring
    ↓
┌───────────────┬────────────────┬─────────────────┐
│   Target      │   Stop-Loss    │   End-of-Day    │
└───────┬───────┴────────┬───────┴────────┬────────┘
        │                │                │
        └────────────────┴────────────────┘
                         ↓
                       Broker
                         ↓
                   Position Closed
```

This separates **signal generation** from **position management**.

A completed candle can generate an entry signal, while an already-open
position can be monitored independently for its exit conditions.

### End-of-Day Flow

The trading session also has an explicit shutdown path.

```text
Trading Session
      ↓
Market Close / Session End
      ↓
Check Open Position
      ↓
Close Position if Required
      ↓
Stop Trading
      ↓
Shutdown Session
```

The session lifecycle is therefore handled by the engine rather than relying
on manually stopping the process.


## Core Components

The engine is divided into focused modules, with each component responsible
for a specific part of the trading lifecycle.

### `live_feed.py`

Handles the real-time market-data connection and processes incoming market
ticks from the broker's WebSocket feed.

It acts as the live data source for the rest of the trading pipeline.

### `websocket_feed.py`

Contains the candle-building logic used to transform incoming ticks into
fixed-timeframe candles.

```text
Live Tick → CandleBuilder → Completed Candle
```

Only completed candles are passed to the strategy for signal generation.

### `strategy.py`

Contains the trading strategy and its internal state.

Responsibilities include:

- Maintaining strategy levels
- Evaluating completed candles
- Generating entry signals
- Managing strategy state
- Preventing unwanted re-entry

The strategy is independent of broker-specific order execution.

### `execution_engine.py`

Acts as the central coordinator between strategy signals, risk management,
position state, and broker execution.

It handles:

- Signal processing
- Risk validation
- Position entry
- Position exits
- Target and stop-loss handling
- End-of-day exits
- PnL updates
- Trade logging

### `risk_manager.py`

Provides the risk-control layer between strategy decisions and order
execution.

It maintains trading constraints such as:

- Daily trade limits
- Daily PnL
- Daily loss protection
- Trading lockout state
- Daily state resets

### `paper_broker.py`

Provides a simulated broker implementation for testing the execution pipeline
without sending live orders.

This allows the same execution architecture to be exercised before using a
live broker.

### `angel_broker.py`

Provides the live broker implementation using Angel One SmartAPI.

It handles broker-side operations such as authentication, order placement,
position management, and order execution responses.

### `broker_adapter.py`

Defines the broker-facing abstraction used to keep execution logic separated
from the specific broker implementation.

This allows the execution layer to work with different broker
implementations without embedding broker-specific behaviour throughout the
system.

### `market_data.py`

Handles market-data operations required by the trading engine, including
retrieving market information and resolving instrument-related data needed by
the live pipeline.

### `market_calendar.py`

Provides market-session awareness and helps prevent the engine from treating
non-trading days as active trading sessions.

### `trading_session.py`

Manages the lifecycle of the trading session, including daily state,
session-level conditions, and end-of-day handling.

### `trade_logger.py`

Records trade activity and execution results for later analysis and
debugging.

### `login.py`

Handles broker authentication and obtains the session information required by
the live trading components.

### `config.py`

Centralizes runtime configuration and loads sensitive environment-specific
values from environment variables rather than storing credentials directly
in source code.


## Risk & Safety Controls

The trading engine places a dedicated risk-control layer between strategy
signals and broker execution.

A strategy signal is treated as a **request to trade**, not as an automatic
instruction to place an order.

```text
Strategy Signal
       ↓
ExecutionEngine
       ↓
RiskManager
       ↓
┌───────────────┐
│ Risk Checks   │
└───────┬───────┘
        │
   ┌────┴─────┐
   │          │
Approved    Rejected
   │          │
   ▼          ▼
 Broker     No Trade
```

### Daily Trade Controls

The engine tracks trading activity during the current session and can prevent
additional entries once the configured daily trade limit has been reached.

This helps prevent repeated entries caused by unexpected market conditions,
duplicate signals, or strategy re-entry.

### Daily PnL Tracking

The risk layer maintains session-level PnL information and uses it as part
of the trading-state decision process.

This allows the system to distinguish between an individual trade result and
the overall state of the current trading session.

### Daily Loss Protection

The risk manager can lock further trading once the configured daily loss
threshold is reached.

```text
Trade Result
     ↓
Update Daily PnL
     ↓
Loss Threshold Reached?
     │
 ┌───┴────┐
 │        │
 NO       YES
 │        │
 ▼        ▼
Continue  Lock Trading
```

### Position Protection

Open positions are monitored for defined exit conditions, including:

- Stop-loss
- Target
- End-of-day exit

The execution layer is responsible for acting on these conditions and
forwarding the required order to the broker.

### Session State Reset

Trading state is reset at the beginning of a new trading session.

This prevents state from a previous trading day from unintentionally carrying
over into the next session.

### Market-Day Protection

The engine includes market-calendar awareness so trading operations are not
started blindly on non-trading days.

### No-Data Protection

Market data is treated as an external dependency and is therefore validated
before being used for trading decisions.

If required data cannot be obtained reliably, the system should avoid
generating a decision from incomplete or invalid information.

### Paper / Live Separation

The execution architecture supports separate paper and live broker
implementations.

This allows the trading pipeline to be exercised without requiring every
test to interact with a live brokerage account.

```text
                     ExecutionEngine
                           │
                    Risk Validation
                           │
                           ▼
                     Broker Layer
                     ┌─────┴─────┐
                     │           │
                     ▼           ▼
                PaperBroker  AngelBroker
```

The separation between strategy, risk management, and broker execution is
intended to make the system safer to test and easier to evolve.


## Reliability & Failure Handling

A trading engine depends on external systems that can fail independently of
the application. The project therefore treats API availability, market data,
WebSocket connections, and session state as explicit failure points.

The engine was developed with failure handling around the following areas:

- Broker API failures
- Historical candle retrieval failures
- WebSocket connection failures
- Missing or invalid market data
- Non-trading days
- Daily session state
- End-of-day shutdown
- Position and execution state

### API Retry Handling

Historical market-data requests can fail due to temporary API or network
conditions.

The data-fetching layer includes retry behaviour so that a transient failure
does not immediately terminate the trading process.

```text
Market Data Request
        ↓
     Success?
    ┌────┴────┐
    │         │
   YES        NO
    │         │
    ▼         ▼
Continue    Retry
              │
              ▼
        Retry Limit / Failure
              │
              ▼
        Fail Safely
```

The retry mechanism is particularly important for autonomous operation because
the system may be running without manual intervention.

### WebSocket Failure Handling

Live trading depends on a persistent WebSocket connection for market data.

The engine therefore treats WebSocket failures as a recoverable runtime
condition rather than assuming that the connection will remain available
indefinitely.

The live process can detect connection failures and move through its
reconnection/recovery path instead of silently continuing without market data.

### Market-Day Guard

The engine includes market-calendar validation before trading activity begins.

```text
Scheduled Start
      ↓
Market Day?
   ┌──┴──┐
   │     │
  YES    NO
   │     │
   ▼     ▼
Start   Skip
Trading Session
```

This prevents an automated deployment from blindly starting a trading session
on a non-trading day.

### Invalid or Missing Data

External market data is treated as untrusted input.

Before market information is used by the trading pipeline, required values
must be available and valid.

If the required data cannot be obtained reliably, the system should avoid
creating trading decisions from incomplete information.

### Session State Management

Trading state is explicitly maintained and reset at the appropriate session
boundaries.

This includes state related to:

- Strategy levels
- Trades taken during the session
- Position state
- Daily PnL
- Risk controls
- Session lifecycle

Explicit state management prevents information from a previous session from
being unintentionally reused.

### End-of-Day Handling

The engine has an explicit end-of-day path for closing or handling open
positions and terminating the trading session.

```text
Trading Session
      ↓
Session End
      ↓
Position Check
      ↓
Required Exit
      ↓
Stop New Trading
      ↓
Shutdown
```

This is particularly important for an autonomous system where leaving the
process running indefinitely is not an acceptable session-management
strategy.

### Fail-Safe Principle

A core design principle of the engine is:

> **When a required external dependency becomes unreliable, the system should
> fail safely rather than make a trading decision from uncertain data.**

This principle influenced the implementation of retries, market-day checks,
data validation, WebSocket handling, and session shutdown behaviour.


## Testing

The engine was developed and tested incrementally as individual components
and the overall architecture evolved.

Testing was used not only to verify the expected trading path, but also to
validate state transitions, failure handling, session behaviour, and
integration between components.

### Testing Areas

The project includes tests and verification for areas such as:

- Strategy behaviour
- Opening-level calculation
- Candle construction
- Risk-management rules
- Broker behaviour
- Execution flow
- Daily state resets
- Trading-session lifecycle
- End-of-day handling
- WebSocket integration
- Historical market-data retrieval
- API retry behaviour
- Paper-trading execution
- Live execution integration

### Unit-Level Testing

Individual components were tested independently where possible before being
connected to the complete trading pipeline.

This made it easier to isolate issues in strategy logic, risk controls,
execution behaviour, and session state without requiring a live brokerage
connection for every test.

### Integration Testing

The project also includes integration tests for interactions between the
major components.

A typical integration path is:

```text
Market Data
     ↓
Candle Construction
     ↓
Strategy
     ↓
ExecutionEngine
     ↓
RiskManager
     ↓
Broker
     ↓
Trade Logger
```

Testing the components together helped identify issues that would not be
visible when testing individual functions in isolation.

### Failure-Path Testing

External dependencies were tested under failure conditions rather than only
under successful responses.

For example, historical market-data retrieval was tested with simulated
failures to verify that the retry mechanism behaves as expected.

```text
Request
   ↓
Simulated Failure
   ↓
Retry
   ↓
Successful Response
   ↓
Continue Processing
```

This approach makes failure recovery testable without intentionally causing a
real brokerage or market-data failure.

### Session & State Testing

Trading systems maintain state across candles, trades, and the trading day.

The project therefore includes testing around:

- New-session initialization
- Daily state resets
- Trade limits
- Position state
- End-of-day behaviour
- Re-entry conditions
- Session shutdown

These tests are particularly important because state-related bugs can remain
hidden when only individual functions are tested.

### Live Integration Verification

The final stages of development involved verifying the complete pipeline
against live market infrastructure.

This included validating:

```text
Broker Authentication
        ↓
Market Data Connection
        ↓
Live Tick Processing
        ↓
Candle Construction
        ↓
Strategy Evaluation
        ↓
Risk Validation
        ↓
Order Execution
        ↓
Position Management
        ↓
Trade Logging
```

The system was progressively moved from isolated testing and historical
backtesting towards paper execution and finally live execution.

### Testing Philosophy

The main testing principle for the project was:

> **Test both the expected path and the failure path.**

For an autonomous system, successful execution is only one part of
correctness. The system also needs predictable behaviour when data is
missing, APIs fail, connections drop, or a trading session changes state.


## Backtesting & Research

The live trading engine was preceded by a separate phase of historical
research and strategy experimentation.

The purpose of this phase was to evaluate different ideas using historical
market data before integrating a strategy into the live execution pipeline.

### Research Workflow

```text
Historical Market Data
        ↓
Data Preparation
        ↓
Strategy Experiment
        ↓
Backtest
        ↓
Trade Analysis
        ↓
Strategy Refinement
        ↓
Execution Integration
```

The repository contains multiple backtesting and research implementations
developed during this process.

These experiments covered areas such as:

- Opening-range breakout strategies
- Previous-day high/low breakout logic
- Multi-stock backtesting
- Historical index testing
- VWAP and pivot-based approaches
- Entry and exit condition experiments
- Risk-based position sizing
- Capital and PnL tracking
- Drawdown analysis
- Trade-level result analysis

### Strategy Development

Backtesting was used as a research tool rather than as a guarantee of future
performance.

The process helped identify issues in strategy logic, entry conditions,
position management, and risk assumptions before moving the system towards
live execution.

```text
Strategy Idea
     ↓
Historical Test
     ↓
Identify Behaviour
     ↓
Modify / Refine
     ↓
Retest
     ↓
Paper Execution
     ↓
Live Integration
```

### Separation from the Live Engine

The research and backtesting code is kept conceptually separate from the
live execution architecture.

This separation allows strategy ideas to be experimented with without
coupling research code directly to the live broker or trading session.

The live system consumes the strategy through a defined execution pipeline:

```text
Research / Backtesting
        ↓
Validated Strategy Logic
        ↓
Live Strategy Module
        ↓
ExecutionEngine
        ↓
RiskManager
        ↓
Broker
```

### Research Lessons

The backtesting phase highlighted an important limitation of historical
simulation: a strategy can behave differently once it encounters live market
data, execution latency, broker constraints, incomplete information, and
real-time state transitions.

For that reason, the project treats backtesting as one stage of validation
rather than the final proof of a trading system.

The progression became:

```text
Backtesting
    ↓
Paper Trading
    ↓
Integration Testing
    ↓
Live Market Data
    ↓
Live Execution
```


## Paper Trading → Live Execution

The engine was developed through progressively more realistic execution
stages rather than moving directly from backtesting to live orders.

```text
Strategy Development
        ↓
Historical Backtesting
        ↓
Paper Broker
        ↓
Integration Testing
        ↓
Live Market Data
        ↓
Live Execution
```

### Historical Backtesting

Initial strategy ideas were evaluated against historical market data.

This stage was primarily used to understand strategy behaviour, identify
logic issues, and refine entry, exit, and risk assumptions.

### Paper Trading

The execution layer was then connected to a simulated broker.

This allowed the complete signal-to-execution pipeline to be exercised without
placing real brokerage orders.

```text
Market Data
     ↓
Strategy
     ↓
ExecutionEngine
     ↓
RiskManager
     ↓
PaperBroker
     ↓
Trade Result
```

Paper execution provided a controlled environment for validating:

- Signal handling
- Position state
- Risk checks
- Entry and exit flow
- PnL tracking
- Trade logging
- Session behaviour

### Integration Testing

After individual components and paper execution were validated, the system
was tested as an integrated pipeline.

This stage focused on interactions between:

- Live market data
- Candle construction
- Strategy state
- Risk management
- Execution
- Position monitoring
- Session management

### Live Market Data

The next stage introduced real-time market data through the broker's
WebSocket infrastructure.

This allowed the engine to process actual market ticks and construct
timeframe candles in real time.

The live data path is:

```text
Broker WebSocket
       ↓
Live Ticks
       ↓
CandleBuilder
       ↓
Completed Candles
       ↓
Strategy
```

### Live Execution

The final execution stage connected the trading pipeline to the live broker
implementation.

The resulting flow is:

```text
Live Market Data
       ↓
Strategy Signal
       ↓
Risk Validation
       ↓
Live Broker
       ↓
Position
       ↓
Live Position Monitoring
       ↓
Exit
       ↓
Trade Logging
```

The separation between the strategy, risk layer, and broker implementation
makes it possible to change the execution environment without rewriting the
entire trading system.

### Why the Progression Matters

The project treats live execution as the final stage of a validation process,
not as the first environment for testing new logic.

Each stage exposed a different class of problems:

```text
Backtesting
    ↓
Strategy & Logic Issues

Paper Trading
    ↓
Execution & State Issues

Integration Testing
    ↓
Component Interaction Issues

Live Market Data
    ↓
Real-Time & Connection Issues

Live Execution
    ↓
Broker & Operational Issues
```

This progression helped reduce the gap between a strategy that works in
historical data and a system that can operate continuously in a real-time
environment.


## Deployment

The live trading engine is deployed on a Linux VPS and runs as an autonomous
background service.

The deployment uses `systemd` to manage the trading process and its lifecycle,
allowing the engine to start according to the configured schedule without
requiring manual intervention.

### Deployment Flow

```text
Trading Schedule
       ↓
systemd
       ↓
Trading Service
       ↓
main_live.py
       ↓
Trading Session
       ↓
Live Market Data
       ↓
Strategy + Risk + Execution
       ↓
Session Shutdown
```

### Autonomous Startup

The trading process is configured as a system service so that the engine can
be started automatically according to the trading schedule.

This removes the need to manually launch the application before each trading
session.

### Session Lifecycle

Once started, the service initializes the trading environment and enters the
configured trading session.

```text
Service Start
     ↓
Authentication
     ↓
Market-Day Validation
     ↓
Market Data Initialization
     ↓
Trading Session
     ↓
Position Management
     ↓
End-of-Day Handling
     ↓
Graceful Shutdown
```

### Process Management

Using `systemd` provides process-level management outside the Python
application itself.

This separates:

- Application logic
- Trading-session logic
- Operating-system process management

The Python application is responsible for trading behaviour, while the
operating system manages the long-running service.

### Logging & Monitoring

The deployed service can be inspected through the Linux service and logging
infrastructure.

This makes it possible to investigate:

- Service startup
- Authentication failures
- Market-data issues
- WebSocket events
- Trading activity
- Runtime exceptions
- Session shutdown

The deployment therefore provides an operational layer around the trading
engine rather than treating the Python process as a manually executed script.

### Graceful Shutdown

The trading session has an explicit shutdown path rather than relying only on
terminating the Python process.

The intended lifecycle is:

```text
Trading Active
      ↓
Session End
      ↓
Handle Open Position
      ↓
Stop New Entries
      ↓
Close / Finalize Session
      ↓
Shutdown
```

This is particularly important for an autonomous trading system because
startup, runtime operation, and shutdown all need predictable behaviour.


## Configuration & Security

Environment-specific configuration is kept outside the source code.

The engine loads sensitive credentials and private trading configuration from
environment variables rather than storing them directly in Python files.

### Environment Configuration

A `.env.example` file is provided as a template:

```text
.env.example
```

The local environment can provide values such as:

```env
ANGEL_API_KEY=
ANGEL_CLIENT_CODE=
ANGEL_PASSWORD=
ANGEL_TOTP_SECRET=
ANGEL_SYMBOL=
```

The actual `.env` file is intentionally excluded from version control.

### Credential Separation

Authentication values are loaded through the configuration layer and passed
to the components that require them.

```text
Environment Variables
        ↓
     config.py
        ↓
 Authentication / Broker
        ↓
 Live Trading Components
```

This keeps credentials out of the trading logic and prevents authentication
details from being distributed across multiple source files.

### Private Trading Configuration

Trading-specific environment configuration is also kept outside the public
source code.

This allows the same codebase to be used with different runtime
configurations without changing the application's source code.

### Git Protection

The repository uses `.gitignore` rules to prevent sensitive and generated
files from being committed.

The public repository contains:

- `.env.example`
- Source code
- Documentation
- Configuration structure

It does **not** contain:

- API credentials
- Authentication secrets
- Local `.env` files
- Runtime trade logs
- Generated output files
- Private environment configuration

### Security Principle

The guiding principle is:

> **Configuration belongs outside the application source code.**

The application should consume credentials and environment-specific settings
through configuration rather than embedding them directly into the codebase.


## Project Structure

The repository is organized around the live trading pipeline, broker
abstraction, risk management, session management, and supporting research
tools.

```text
Stock-Bot/
│
├── main_live.py
│
├── config.py
├── login.py
│
├── live_feed.py
├── websocket_feed.py
├── market_data.py
├── market_calendar.py
├── instrument_lookup.py
│
├── strategy.py
├── execution_engine.py
├── risk_manager.py
│
├── broker_adapter.py
├── angel_broker.py
├── paper_broker.py
│
├── trade_logger.py
├── trading_session.py
│
├── backtester.py
├── backtester2.py
├── backtester3.py
├── multiple_backtest.py
├── MultiStock_tester.py
├── nifty_orb_backtest.py
├── vwap_pivot_backtest.py
├── banknifty_backtester.py
├── Data_fetcher.py
│
├── integration_test.py
├── demo_test.py
├── testing.py
├── eod_reentry_test.py
└── eod_watchdog_reentry.py
```

### Runtime Components

```text
main_live.py
     │
     ├── Authentication
     │
     ├── Market Data
     │      ├── live_feed.py
     │      ├── websocket_feed.py
     │      └── market_data.py
     │
     ├── Strategy
     │      └── strategy.py
     │
     ├── Risk & Execution
     │      ├── risk_manager.py
     │      └── execution_engine.py
     │
     ├── Broker
     │      ├── broker_adapter.py
     │      ├── paper_broker.py
     │      └── angel_broker.py
     │
     └── Session & Logging
            ├── trading_session.py
            └── trade_logger.py
```

### Supporting Research

The backtesting and research modules are kept separate from the live
execution path.

They are used for:

- Historical strategy evaluation
- Market-data experiments
- Multi-stock analysis
- Entry and exit research
- Performance analysis
- Strategy iteration

This separation keeps experimental research code from becoming tightly
coupled to the live trading infrastructure.


## Tech Stack

### Core

- **Python** — Application and trading-engine logic

### Brokerage & Market Data

- **Angel One SmartAPI** — Broker integration and market-data access
- **SmartWebSocketV2** — Real-time market-data streaming

### Data & Analysis

- **pandas** — Market-data processing and trade analysis
- **NumPy** — Numerical processing used in research and backtesting
- **yfinance** — Historical market-data retrieval for research and backtesting

### Authentication & Configuration

- **PyOTP** — Time-based authentication support
- **python-dotenv** — Environment-based configuration management

### Deployment

- **Linux** — Runtime environment
- **systemd** — Service and process management

### Development

- **Git** — Version control
- **GitHub** — Source-code hosting and project management


## Engineering Principles

The system evolved around several engineering principles that became
increasingly important as the project moved from a simple strategy script to
an autonomous trading engine.

### Separation of Responsibilities

Each major concern has its own component.

Market data, strategy logic, risk management, execution, broker integration,
logging, and session management are kept separate rather than being combined
into one trading script.

### Risk Before Execution

A strategy signal is a request to trade, not an instruction to place an order.

The signal must pass through the risk-management layer before reaching the
broker.

```text
Strategy
   ↓
Signal
   ↓
Risk Validation
   ↓
Broker
```

This keeps trading decisions separate from the decision to actually execute
them.

### Explicit State Management

Trading systems depend heavily on state.

The engine explicitly manages state related to:

- Current trading session
- Strategy levels
- Open positions
- Trades taken during the session
- Daily PnL
- Risk controls

Explicit state makes session transitions and resets predictable.

### Fail Safely

External systems such as broker APIs and WebSocket connections can fail.

The engine therefore treats external dependencies as unreliable inputs and
uses validation, retry, recovery, and shutdown paths rather than assuming
that every request will succeed.

### Test Failure Paths

Correct behaviour is not limited to successful execution.

The project also tests situations such as:

- API failures
- Missing market data
- Session transitions
- State resets
- Connection problems
- End-of-day handling

Testing failure paths is particularly important for an autonomous system.

### Separate Research from Execution

Backtesting and strategy experimentation are kept separate from the live
execution pipeline.

This allows new ideas to be investigated without directly coupling research
code to live broker execution.

### Automate the Lifecycle

An autonomous system should not depend on manually starting, monitoring, and
terminating the application every day.

The project therefore treats startup, session management, monitoring, and
shutdown as explicit parts of the system lifecycle.

### Configuration Outside Source Code

Credentials and environment-specific settings are loaded through environment
configuration rather than being embedded directly into application code.

This keeps the same codebase adaptable across different runtime
environments while reducing the risk of accidentally exposing secrets.


## What I Learned Building This

This project started as an attempt to automate a trading strategy and gradually
became a much broader software-engineering project.

The biggest lessons came from the gap between making a strategy work and
making an autonomous system operate reliably.

### Real-Time Systems Are State Machines

In a live environment, the system is continuously transitioning between
states: waiting for market data, building candles, waiting for a signal,
holding a position, exiting, and shutting down.

Making these transitions explicit is much more reliable than relying on
implicit state spread across individual functions.

### APIs Are Not Reliable Dependencies

Broker and market-data APIs can fail, timeout, return unexpected responses,
or disconnect.

Building retry, validation, and recovery paths taught me that external
dependencies have to be treated as failure points rather than guaranteed
inputs.

### Strategy and Execution Are Different Problems

A trading strategy answers:

> "Should I trade?"

The execution system has to answer:

> "Can I trade, how should the order be handled, and what happens after the
> position is opened?"

Keeping those responsibilities separate made the architecture much easier to
reason about and test.

### Live Data Changes the Problem

A strategy that works on historical candles does not automatically become a
reliable live system.

Real-time execution introduces problems such as:

- Incomplete candles
- WebSocket disconnects
- API failures
- Timing and state transitions
- Position synchronization
- End-of-day handling

Moving from backtesting to live data therefore required a different level of
engineering discipline.

### Failure Paths Matter as Much as the Happy Path

One of the biggest lessons from the project was that reliability is mostly
about deciding what happens when something goes wrong.

Instead of only designing:

```text
Success → Continue
```

the system also needs explicit paths for:

```text
Failure
   ↓
Detect
   ↓
Recover / Retry
   ↓
Validate
   ↓
Continue or Fail Safely
```

### Deployment Is Part of the System

Getting the Python code to work locally was only one part of the project.

Running the engine autonomously required thinking about:

- Process management
- Scheduled startup
- Logging
- Session lifecycle
- Shutdown behaviour
- Runtime configuration

Deploying the system made it clear that software is not finished when the
code runs once; it also has to behave predictably in its operating
environment.

### Testing Must Include the Unusual Cases

Testing successful execution is not enough for an autonomous system.

The project made me pay much more attention to:

- API failures
- State resets
- Re-entry conditions
- Session boundaries
- Missing data
- Connection failures
- End-of-day behaviour

These cases often reveal more about the quality of a system than the normal
execution path.

### Building the System Was More Valuable Than the Strategy

The most valuable outcome of this project was not the trading strategy itself.

It was learning how to design, connect, test, deploy, and operate a system
that depends on real-time data and external services.

That shifted the project from a simple trading script into an exploration of
**event-driven architecture, state management, reliability, API integration,
risk controls, and autonomous deployment.**


## Project Status

**Current Version: v1.0**

The project has progressed through the following stages:

```text
Strategy Development
        ↓
Historical Backtesting
        ↓
System Architecture
        ↓
Paper Trading
        ↓
Integration Testing
        ↓
Live Market Data
        ↓
Automated Live Execution
        ↓
VPS Deployment
```

### Current Capabilities

The current engine supports:

- Real-time market-data processing
- Candle construction from live ticks
- Strategy-based signal generation
- Dedicated risk validation
- Paper and live broker execution
- Live position monitoring
- Target and stop-loss handling
- End-of-day session handling
- Trade logging
- Market-day validation
- API retry and recovery
- Automated VPS deployment

### Current Focus

Development is continuing around:

- Reliability
- Observability
- Failure recovery
- Testing
- Deployment robustness
- Maintainability
- Improving the separation between research and live execution

The project is considered **v1.0** because the core end-to-end trading pipeline
is operational, while the surrounding infrastructure continues to evolve.


## Disclaimer

This project is provided for educational and engineering purposes.

Automated trading involves financial risk. Nothing in this repository should
be interpreted as financial advice, an investment recommendation, or a
guarantee of trading performance.

The trading engine is a software-engineering project intended to demonstrate
real-time data processing, event-driven architecture, risk management,
broker integration, automation, and system deployment.