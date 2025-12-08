# Options Testing Framework

This library is a framework for testing stock options strategies. It works along with the popular Backtrader framework. The Backtrader framework is an excellent solution for backtesting stock trading ideas. 
However, testing options trading strategies is much more complicated. This
framework will work with backtrader to test your options trading strategies.

## The Options Chain class
The options chain class receives the raw data from the data loader and creates option objects that can be used by the rest of the library.

## The Options Portfolio class
This is the class that is directly called from the external program. It is where opening and closing of positions is initiated and communicated to the rest of the program. It keeps a reference to open positions, and also closed positions. This is available to the the external program for evaluating its positions. 

## The OptionCombination class
This is the base class for any options position, even a single option. It can hold one or more options that are part of an option spread.

## Option Spreads
Several common option spread classes are available for convenience. Of course, you can also create any kind of option position with the "custom" type option spread class.

## Events

To make coordinating the different modules easier, events cause changes in modules as a result of the timeslot advancing and all the value changes for each advance. There are also events to assure that the portfolio value accurately reflects anything that changes its value, such as option price changes and fees.

### Dispatchers

#### The following classes implement the Dispatcher class and emit events

* OptionsPortfolio
  * events: new_position_opened, position_closed, next, next_options position_expired
* Option
  * open_transaction_completed, close_transaction_completed, option_expired, fees_incurred

### Event Handling

#### next

* Emitted by the OptionPortfolio. The "next" method is called externally when time advances. The option chain needs to get updates with a new time slot's data. 
* Handled by OptionChain.

  * OptionChain handler: on_next - updates all the option data for the given timeslot

#### next_options

* Emitted by OptionPortfolio. The "next_options" method emits all the open options. The OptionChain updates each option using the current quote data
* Handled by OptionChain. 

#### position_closed

* Emitted by OptionPortfolio when an option position is closed. This is so an external program can receive this event.
* There are no event handlers in the library for this event. It is provided for the external program to get final price and other information when a position is closed.

#### position_expired

* Emitted by OptionPortfolio when an option expires. This is so an external program can receive this event.
* There are no event handlers in the library for this event. It is provided for the external program to get final price and other information when a position has expired.

#### open_transaction_completed

* Emitted by the Option class. It alerts the portfolio that an option has been opened. 
* Handled by OptionPortfolio. The portfolio needs to know how much premium was bought/sold so it can update its cash position. It also adds the position to its open positions list.

#### close_transaction_completed

* Emitted by the Option class. It alerts the portfolio that an option has been closed. 
* Handled by OptionPortfolio. The portfolio removes the position from its open positions and moves it to its closed positions. Also, final premium is used to update its cash position.

#### option_expired

* Emitted by the Option class. It alerts when the time slot reaches the expiration date while the option is still open.
* Handled by the OptionPortfolio. Similar to the close transaction event.

#### fees_incurred

* Emitted by the Option class. It alerts whenever any fees have been incurred.
* Handled by the OptionPortfolio class. It needs to update its cash position to account for any fees.












