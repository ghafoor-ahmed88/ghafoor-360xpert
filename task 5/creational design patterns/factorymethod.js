class Transport{
    deliver(){
        throw "Method not implemented";
    }
}

class Truck extends Transport{
    deliver(){
        console.log("Deliver by land(Truck)")
    }
}

class Ship extends Transport{
    deliver(){
        console.log("Deliver by Sea(Ship)")
    }
}
class plane extends Transport{
    deliver(){
        console.log("Deliver by Air(Plane)")
    }
}

class Logistics{
    createTransport(){
        throw "Factory method"
    }

    planDelivery(){
        const transport = this.createTransport();
        transport.deliver();
    }
}

class RoadLogistics extends Logistics{
    createTransport(){
        return new Truck();
    }
}

class SeaLogistics extends Logistics {
    createTransport() {
        return new Ship(); 
    }
}
class airlogistics extends Logistics {
    createTransport(){
        return new plane();
    }
}

const roadLogistics = new RoadLogistics();
roadLogistics.planDelivery();

const seaLogistics = new SeaLogistics();
seaLogistics.planDelivery();

const Airlogistics = new airlogistics
Airlogistics.planDelivery(); 
