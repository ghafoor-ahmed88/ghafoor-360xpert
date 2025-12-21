class OldPayment {
  payAmount(amount) {
    console.log("Paid:", amount);
  }
}

class PaymentAdapter {
  constructor(oldPayment) {
    this.oldPayment = oldPayment;
  }

  pay(data) {
    this.oldPayment.payAmount(data.amount);
  }
}

const payment = new PaymentAdapter(new OldPayment());
payment.pay({ amount: 500 });
