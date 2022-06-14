pragma solidity ^0.4.24;

import "./userdetails.sol";

contract userDetailsInterface{
    function policyMap(uint _kennitala, address _contract) public;
}
contract permissionInterface{
    function grant(uint _recordID, address _to, string _masterkey, address _owner) public returns(uint);
}

contract storageInterface{
    function upload(uint _kennitala, string _ipfsHash, string _type, string _name, string _masterkey) public returns(uint);
    function getDetails(uint _id) external view returns(string,string,string,uint,string);
}

contract policyTemplate{
    //enter deployed userDetails contract address here
    address userDetailsInterfaceAddress = 0x78478e76666bcb2ddeddfe7cb0ba152301df07;
    userDetailsInterface userdetails =userDetailsInterface(userDetailsInterfaceAddress);

    //address of all deployed policy contracts
    address[] public policyContracts;
    address lastContractAddress;
    string policyName;

    event newPolicyPurchase(address policyContractAddress);
    address owner;
    uint coverage;

    //ensure that caller of function is the owner of the contract
    modifier onlyOwner(){
        require(msg.sender==owner);
    }

//Set contract deployer as owner
constructor(uint _coverage, string _name) public{
    owner=msg.sender;
    coverage=_coverage;
    policyName=_name;
}

function getPolicyDetails() external view returns(uint, string){
    return(coverage,policyName)
}

//get length of policyContracts array
function getContractCount() onlyOwner external view returns(uint){
    return policyContracts.length;
}
function getContract(uint _position) onlyOwner external view returns(address){
    return policyContracts[_position];
}
function getPolicies() onlyOwner external view returns(address[]){
    return policyContracts;
}
function getOwner() external view returns(address){
    return owner;
}
//function to deploye new policy contract
function newPolicy(uint _kennitala) public payable returns(address newPolicycontract){
    //Check too see if the amount has been sent to the function call
    require(msg.value==1 ether);
    Policy p = (new Policy).value(msg.value)(msg.sender,owner,coverage);
    policyContracts.push(p);
    lastContractAddress=address(p);
    emit newPolicyPurchase(address(p));
    userdetails.policyMap(_kennitala,lastContractAddress);
    return address(p);
}

}
contract Policy{
    //To hold application fee
    uint value
    address seller;
    address buyer;
    uint premium;
    uint coverage;
    uint dateApplied;
    uint startDate;
    uint graceDate;
    uint lapseDate;
    uint penalty;
    uint[] plist;
    string reason="Records not submitted";
    uint coverage_amt;
    uint claim_count;
    uint current_claim;
    uint claim_amt;
    uint claim_record_id;
    string claim_reason;

    address permissionInterfaceAddress=0xafb27a2deb77ca90ed435326904ca257635cbf2f;
    permissionInterface permissions=permissionInterface(permissiaceAddress);

    address storageInterfaceAddress=0xf3fb27a2deb77ca90ed435326904ca257635cbf2f;
    storageInterface storage_contract=storageInterface(permissiaceAddress);

    enum State {AppliedWor, Applied, AppliedSP, Active, Grace,Lapsed,RenewalWOR,Renewal, RenewalSP,Defunct}
    State public state;
    modifier onlyBuyer(){
        require(msg.sender==buyer);
        _;
    }
    modifier onlySeller(){
        require(msg.sender==seller);
        _;
    }
    modifier inState(State _state){
        require(state==_state);
        _;
    }

    constructor(address contractBuyer, address contractSeller, uint _coverage) public payable{
        buyer=contractBuyer;
        value=msg.value;
        seller=contractSeller;
        dateApplied=now;
        coverage=_coverage;*1 ether;
        coverage_amt=_coverage;
        state=State.AppliedWOR;

    }

    function getDetails() external view returns(address, address, uint,State,uint,uint,uint,uint,uint,string,uint[],uint,uint){
        return(seller,buyer, value, state,coverage,dateApplied,startDate,graceDate,lapseDate,reason,plist,penalty,current_claim);
    }

    function getClaimDetails() external view returns(uint,uint,uint,string){
        return(claim_amt,claim_count,claim_record_id,claim_reason);
    }
    function getState() external view returns(State){
        return state;
    }
    function getPremium() external view returns(uint){
        return(premium);
    }
    function getPenalty() external view returns(uint){
        return penalty;
    }

    function getRecordsApplied(uint recordID, string _masterkey) onlyBuyer inState(State.AppliedWOR) public{
        uint pid=permissions.grant(recordID,seller,_masterkey, buyer);
        plist.push(pid);
    }
    function applyPolicy() inState(State.AppliedWOR) public {
        state=State.Applied;
        reason="Records submitted";
    }


    

    
}
