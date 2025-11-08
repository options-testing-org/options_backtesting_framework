# Options Testing Framework

This library is a framework for testing stock options strategies. It works along with the popular Backtrader framework. The Backtrader framework is an excellent solution for backtesting stock trading ideas. 
However, testing options trading strategies is much more complicated. This
framework will work with backtrader to test your options trading strategies.

## The Test Manager class
The test manager class basically organizes the different components. On init, it instantiates the correct data loader, a new portfolio and a new options chain. It also binds the portfolio and data loader so the loading of any new data can be coordinated.

## The Options Chain class
The options chain class receives the raw data from the data loader and creates option objects that can be used by the rest of the library.

## The Options Portfolio class
This is the class that is directly called from the external program. It is where opening and closing of positions is initiated and communicated to the rest of the program. It keeps a reference to open positions, and also closed positions. This is available to the the external program for evaluating its positions. 

## The OptionCombination class
This is the base class for any options position, even a single option. It can hold one or more options that are part of an option spread.

## Option Spreads
Several common option spread classes are available for convenience. Of course, you can also create any kind of option position with the "custom" type option spread class.

## Event Driven

To avoid getting data when it isn't needed, the architecture is event-driven. There is a lot of data in the options chain, so we want to avoid getting data when we don't
need it. It also allows a much simpler architecture because it eliminates the need for direct references to objects following the "loose coupling" paradigm. 

## Dispatchers

### The following classes emit events

* DataLoader and inheriting classes
  * events: option_chain_loaded
* OptionsPortfolio
  * events: new_position_opened, position_closed, next, position_expired
* Option
  * open_transaction_completed, close_transaction_completed, option_expired, fees_incurred

### Event Handling

#### option_chain_loaded

* Emitted by DataLoader class when an option chain has been loaded from the data
* Handled by the "on_option_chain_loaded" method of the OptionChain class. This method converts the raw pandas dataframe rows into Option objects that can be used by the rest of the program.

#### next

* Emitted by the OptionPortfolio. The "next" method is called externally when options being held by the portfolio need to have their data updated with a new time slot's data. It then emits the "next" event to let objects know they need to update thier data.
* Handled by both the OptionCombination and Option objects.
  * OptionCombination handler: next_quote_date - updates date to the new time slot
  * Option handler: next_update - updates price and other values for the new time slot

#### new_position_opened

* Emitted by OptionPortfolio. The external program executes the "open_position" method on the portfolio object. The event lets the data loader know to go and get all the updates for the options so they are available throughout the life of the option position.
* Handled by DataLoaders. The data loader gets the options data up until expiration. It then attaches the data to each option passed in to the event so the option can update itself when "next" is called on it

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












