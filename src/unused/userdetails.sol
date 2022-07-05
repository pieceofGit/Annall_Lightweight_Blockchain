pragma solidity ^0.4.24;

contract userDetails{
    event addressLinked(address _address, uint _kennitala);
    event keyLinked(address _address, string _ipfshash);
    //Create mapping key=>value: address=>kennitala
    mapping(uint=>address) public kennitalaToAddress;
    //Create mapping  key=>value: kennitala=>address
    mapping(address=>uint) public addressToKennitala;
    //Create mapping between address and pgp file stored on ipfs
    mapping(address=>string) public ownerToKey;
    //Create mapping between users kennitala and policy contract
    mapping(uint=>address) public ownerToPolicy;

    //function to link kennitala to user´s ethereum address
    function link(uint _kennitala, string _ipfskey) public{
        //ensure user can call this function only once
        //ensure one to one mapping between users address and kennitala card
        require(kennitalaToAddress[_kennitala]==0x000000000000000000000000000000000000000,"kennitala already exists");
        require(addressToKennitala[msg.sender]==0,'Address already used');
        //ensure key pair has not been generated for user
        require(bytes(ownerToKey[msg.sender]).length==0,"Key pair for user already exist");

        //map msg.sender to kennitala card no.
        kennitalaToAddress[_kennitala]=msg.sender;
        addressToKennitala[msg.sender]=_kennitala;

        //fire event for logging
        emit addressLinked(msg.sender, _kennitala);

        //map address to key file on ipfs
        ownerToKey[msg.sender]=_ipfskey;

        //fire event for logging
        emit keyLinked(msg.sender, _ipfskey);
    }

    function login(uint kennitala) external view returns(bool){
        //ensure valid, registered users call this function
        require(kennitalaToAddress[_kennitala]!=0x000000000000000000000000000000000000000, "Account does not exist");
        //check if msg.sender
        return(kennitalaToAddress[_kennitala]==msg.sender);
    }
        
    function getAddress(uint _kennitala) external view returns(kennitala){
        return(kennitalaToAddress[_kennitala]);
    }
    function getKeyHash(uint _kennitala) external view returns(string){
        return(ownerToKey[kennitalaToAddress[_kennitala]]);
    }
    function policyMap(uint _kennitala, address _contract) public{
        ownerToPolicy[_kennitala]=_contract;

    }
    function getPolicyMap(uint _kennitala) external view returns(address){
        return(ownerToPolicy[_kennitala]);
    }

    }



}