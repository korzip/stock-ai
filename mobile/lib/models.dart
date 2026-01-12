class Instrument {
  final int id;
  final String marketCode;
  final String symbol;
  final String name;
  final String currency;

  Instrument({
    required this.id,
    required this.marketCode,
    required this.symbol,
    required this.name,
    required this.currency,
  });

  factory Instrument.fromJson(Map<String, dynamic> j) => Instrument(
        id: j['id'] as int,
        marketCode: (j['market_code'] ?? j['marketCode']) as String,
        symbol: j['symbol'] as String,
        name: j['name'] as String,
        currency: j['currency'] as String,
      );
}

class DailyPrice {
  final String tradingDate;
  final double? close;
  final int? volume;

  DailyPrice({required this.tradingDate, this.close, this.volume});

  factory DailyPrice.fromJson(Map<String, dynamic> j) => DailyPrice(
        tradingDate: j['trading_date'] as String,
        close: (j['close'] == null) ? null : (j['close'] as num).toDouble(),
        volume: j['volume'] as int?,
      );
}
