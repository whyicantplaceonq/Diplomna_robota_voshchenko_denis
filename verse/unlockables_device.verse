using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/SpatialMath }
using { /UnrealEngine.com/Temporary/Diagnostics }

# Клас, що описує дані про покупку (розблоковуваний елемент)
purchase_data<public> := class<concrete>:
    @editable
    CreativeProps : []creative_prop = array{} # Список обєктів, які будуть переміщені при покупці

    @editable
    Price : int = 0 # Ціна покупки

    @editable
    ClaimerName : string = "" # Ім'я, яке буде показано на білборді

    @editable
    ClaimerLocation : vector3 = vector3{} # Позиція, куди буде телепортовано тригер

# Основний пристрій, який керує розблокуванням елементів
unlockables_device := class(creative_device):

    @editable
    # Кнопка, яка перевіряє наявність золота
    GoldConditionalButton : conditional_button_device = conditional_button_device{}

    @editable
    # Тригер, який активує покупку
    ClaimerTrigger : trigger_device = trigger_device{}

    @editable
    # Білборд для відображення інформації про покупку
    ClaimerBillboard : billboard_device = billboard_device{}

    @editable
    # Відстань переміщення обєктів по осі Z
    DefaultMoveDistance : float = 1500.0

    @editable
    PurchaseDatas : []purchase_data = array{} # Список всіх доступних покупок

        TextForUI<localizes>(InText : string): message = "{InText}"

        var MaybeOwnerAgent : ?agent = false # Агент, який володіє пристроєм
        var CurrentPurchaseIndex : int = 0 # Індекс поточної покупки
        var bBlockTriggerInteraction : logic = false # Блокування повторної взаємодії

        # Ініціалізація пристрою при старті
        OnBegin<override>()<suspends>:void=
            Print("OnBegin")
            GetPlayspace().PlayerRemovedEvent().Subscribe(OnPlayerLeft)
            ClaimerTrigger.TriggeredEvent.Subscribe(OnClaimerTriggered)
            for (PurchaseData : PurchaseDatas):
                MoveProps(PurchaseData, false)
            if (FirstPurchase := PurchaseDatas[0]):
                MoveClaimerToPurchase(FirstPurchase)

        # Обробка виходу гравця
        OnPlayerLeft(Agent : agent):void=
            if(OwnerAgent := MaybeOwnerAgent?, OwnerAgent = Agent):
                set MaybeOwnerAgent = false
                for (I := 0 .. CurrentPurchaseIndex-1, PurchaseData := PurchaseDatas[I]):
                    MoveProps(PurchaseData, false)
                set CurrentPurchaseIndex = 0
                if(FirstPurchaseData := PurchaseDatas[0]):
                    MoveClaimerToPurchase(FirstPurchaseData)

        # Асинхронне розблокування взаємодії з тригером
        AsyncEnableTriggerInteraction()<suspends>:void=
            Sleep(1.0)
            set bBlockTriggerInteraction = false

        # Переміщення обєктів вгору або вниз
        MoveProps(PurchaseData : purchase_data, bMoveUp : logic):void=
            SignedMoveOnZ : float = if (bMoveUp = true)
                then DefaultMoveDistance
                else -DefaultMoveDistance
            for (CreativeProp : PurchaseData.CreativeProps):
                Transform := CreativeProp.GetTransform()
                var Location : vector3 = Transform.Translation
                set Location.Z += SignedMoveOnZ
                if (CreativeProp.TeleportTo[Location, Transform.Rotation]){}

        # Переміщення тригера до позиції покупки та оновлення білборда
        MoveClaimerToPurchase(PurchaseData : purchase_data):void=
            if (ClaimerTrigger.TeleportTo[PurchaseData.ClaimerLocation, IdentityRotation()]){}
            BillboardPriceString : string = if (PurchaseData.Price = 0)
                then "FREE"
                else "{PurchaseData.Price}"
            BillboardString : string = PurchaseData.ClaimerName + "\n" + BillboardPriceString
            ClaimerBillboard.SetText(TextForUI(BillboardString))

        # Обробка активації тригера
        OnClaimerTriggered(MaybeAgent : ?agent):void=
            if (Agent := MaybeAgent?, bBlockTriggerInteraction = false):
                if (OwnerAgent := MaybeOwnerAgent?):
                    if(OwnerAgent <> Agent):
                        Print("Only the Owner Can Purchase!")
                        return
                else:
                    set MaybeOwnerAgent = option{ Agent }
                OwnerGold : int = GoldConditionalButton.GetItemCount(Agent, 0)
                if (CurrentPurchaseData := PurchaseDatas[CurrentPurchaseIndex]):
                    if (OwnerGold < CurrentPurchaseData.Price):
                        Print("Not Enough Money")
                        return
                    set bBlockTriggerInteraction = true
                    spawn{ AsyncEnableTriggerInteraction() }
                    MoveProps(CurrentPurchaseData, true)
                    GoldConditionalButton.SetItemCountRequired(0, CurrentPurchaseData.Price)
                    GoldConditionalButton.Activate(Agent)
                    set CurrentPurchaseIndex +=1
                    if (CurrentPurchaseIndex = PurchaseDatas.Length):
                        var Location : vector3 = ClaimerTrigger.GetTransform().Translation
                        set Location.Z -= DefaultMoveDistance
                        if (ClaimerTrigger.TeleportTo[Location, IdentityRotation()]){}
                    else if (NextPurchaseData := PurchaseDatas[CurrentPurchaseIndex]):
                        MoveClaimerToPurchase(NextPurchaseData)
